"""
Order service for business logic.

This module provides the main business logic for order management,
including syncing, filtering, and event tracking.
"""
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderEvent, OrderStatus, AuditLog
from app.schemas import OrderCreate, OrderSyncResponse
from app.filters.engine import FilterEngine
from app.pricing.engine import PricingEngine
from app.discord.service import DiscordNotificationService


class OrderService:
    """
    Service for managing orders.
    
    Handles order synchronization, filtering, pricing evaluation,
    and event tracking.
    """
    
    def __init__(
        self,
        filter_engine: Optional[FilterEngine] = None,
        pricing_engine: Optional[PricingEngine] = None,
        discord_service: Optional[DiscordNotificationService] = None,
    ):
        """
        Initialize the order service.
        
        Args:
            filter_engine: Filter engine instance
            pricing_engine: Pricing engine instance
            discord_service: Discord notification service instance
        """
        self.filter_engine = filter_engine or FilterEngine()
        self.pricing_engine = pricing_engine or PricingEngine()
        self.discord_service = discord_service
    
    async def sync_orders(
        self,
        db: AsyncSession,
        orders_data: List[OrderCreate],
        timestamp: datetime,
    ) -> OrderSyncResponse:
        """
        Synchronize orders from extension.
        
        Args:
            db: Database session
            orders_data: List of order data from extension
            timestamp: Sync timestamp
            
        Returns:
            Sync response with processed counts
        """
        new_orders = []
        updated_orders = []
        skipped_orders = []
        
        for order_data in orders_data:
            # Check if order exists
            result = await db.execute(
                select(Order).where(Order.id == order_data.id)
            )
            existing_order = result.scalar_one_or_none()
            
            if existing_order is None:
                # Create new order
                new_order = await self._create_order(db, order_data, timestamp)
                new_orders.append(order_data.id)
                
                # Evaluate and potentially notify
                await self._evaluate_new_order(db, new_order)
            else:
                # Update existing order
                was_updated = await self._update_order(
                    db, existing_order, order_data, timestamp
                )
                if was_updated:
                    updated_orders.append(order_data.id)
                else:
                    skipped_orders.append(order_data.id)
        
        return OrderSyncResponse(
            processed=len(orders_data),
            new_orders=new_orders,
            updated_orders=updated_orders,
            skipped_orders=skipped_orders,
        )
    
    async def _create_order(
        self,
        db: AsyncSession,
        order_data: OrderCreate,
        timestamp: datetime,
    ) -> Order:
        """Create a new order."""
        order = Order(
            id=order_data.id,
            url=order_data.url,
            order_type=order_data.order_type,
            status=OrderStatus.PENDING,
            price=order_data.price,
            currency=order_data.currency,
            region=order_data.region,
            queue_type=order_data.queue_type,
            current_rank_tier=order_data.current_rank_tier,
            current_rank_division=order_data.current_rank_division,
            current_rank_lp=order_data.current_rank_lp,
            target_rank_tier=order_data.target_rank_tier,
            target_rank_division=order_data.target_rank_division,
            target_rank_lp=order_data.target_rank_lp,
            duo_required=order_data.duo_required,
            offline_mode=order_data.offline_mode,
            solo_queue_only=order_data.solo_queue_only,
            stream_required=order_data.stream_required,
            requested_wins=order_data.requested_wins,
            requested_games=order_data.requested_games,
            buyer_username=order_data.buyer_username,
            buyer_description=order_data.buyer_description,
            first_seen_at=timestamp,
            last_synced_at=timestamp,
        )
        
        # Apply filters
        passes_filter, reasons = await self.filter_engine.apply_all_rules(db, order)
        if not passes_filter:
            order.is_filtered_out = True
            order.filter_reason = "; ".join(reasons)
        
        db.add(order)
        await db.flush()
        
        # Log creation
        await self._log_audit(db, "ORDER_CREATED", "Order", order.id)
        
        return order
    
    async def _update_order(
        self,
        db: AsyncSession,
        existing_order: Order,
        order_data: OrderCreate,
        timestamp: datetime,
    ) -> bool:
        """
        Update an existing order if there are changes.
        
        Returns:
            True if order was updated, False if no changes
        """
        changes = []
        
        # Check for price change
        if abs(existing_order.price - order_data.price) > 0.01:
            changes.append(("price", str(existing_order.price), str(order_data.price)))
            existing_order.price = order_data.price
        
        # Check for status change (if provided in future)
        # For now, we mainly track price and requirement changes
        
        # Check requirement changes
        req_changes = [
            ("duo_required", existing_order.duo_required, order_data.duo_required),
            ("offline_mode", existing_order.offline_mode, order_data.offline_mode),
            ("solo_queue_only", existing_order.solo_queue_only, order_data.solo_queue_only),
            ("stream_required", existing_order.stream_required, order_data.stream_required),
        ]
        
        for field, old_val, new_val in req_changes:
            if old_val != new_val:
                changes.append((field, str(old_val), str(new_val)))
                setattr(existing_order, field, new_val)
        
        if changes:
            existing_order.updated_at = datetime.utcnow()
            existing_order.last_synced_at = timestamp
            
            # Create events for each change
            for field, old_val, new_val in changes:
                event = OrderEvent(
                    order_id=existing_order.id,
                    event_type=f"CHANGE_{field.upper()}",
                    old_value=old_val,
                    new_value=new_val,
                )
                db.add(event)
            
            await self._log_audit(
                db, "ORDER_UPDATED", "Order", existing_order.id,
                details=f"Changes: {', '.join(c[0] for c in changes)}"
            )
            
            # Send Discord notifications for significant changes
            if self.discord_service and self.discord_service.is_configured():
                for field, old_val, new_val in changes:
                    if field == "price":
                        await self.discord_service.send_order_update_notification(
                            order_id=existing_order.id,
                            order_url=existing_order.url,
                            change_type="Price",
                            old_value=f"${old_val}",
                            new_value=f"${new_val}",
                        )
            
            return True
        
        # Update sync timestamp even if no changes
        existing_order.last_synced_at = timestamp
        return False
    
    async def _evaluate_new_order(self, db: AsyncSession, order: Order) -> None:
        """Evaluate a new order and potentially send notification."""
        # Pricing evaluation
        evaluation = self.pricing_engine.evaluate_order(order)
        
        # Send Discord notification for profitable orders
        if (
            self.discord_service and
            self.discord_service.is_configured() and
            evaluation["is_profitable"] and
            not order.is_filtered_out
        ):
            requirements = []
            if order.duo_required:
                requirements.append("Duo Required")
            if order.offline_mode:
                requirements.append("Offline Mode")
            if order.solo_queue_only:
                requirements.append("Solo Queue Only")
            if order.stream_required:
                requirements.append("Stream Required")
            
            current_rank_str = f"{order.current_rank_tier.value}"
            if order.current_rank_division:
                current_rank_str += f" {order.current_rank_division}"
            if order.current_rank_lp:
                current_rank_str += f" ({order.current_rank_lp} LP)"
            
            target_rank_str = f"{order.target_rank_tier.value}"
            if order.target_rank_division:
                target_rank_str += f" {order.target_rank_division}"
            if order.target_rank_lp:
                target_rank_str += f" ({order.target_rank_lp} LP)"
            
            await self.discord_service.send_new_order_notification(
                order_id=order.id,
                order_url=order.url,
                price=order.price,
                current_rank=current_rank_str,
                target_rank=target_rank_str,
                region=order.region.value,
                requirements=requirements,
            )
    
    async def _log_audit(
        self,
        db: AsyncSession,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor: str = "system",
        details: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Log an audit entry."""
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details,
            success=success,
        )
        db.add(audit_log)
        await db.flush()
