"""
API routes for the FastAPI application.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Order, OrderStatus, FilterRule, Configuration, AuditLog, OrderEvent
from app.schemas import (
    OrderResponse,
    OrderListResponse,
    OrderSyncRequest,
    OrderSyncResponse,
    FilterRuleCreate,
    FilterRuleUpdate,
    FilterRuleResponse,
    ConfigurationResponse,
    ConfigurationCreate,
    ConfigurationUpdate,
    HealthCheckResponse,
    OrderEventResponse,
    AuditLogResponse,
    ApiResponse,
)
from app.services.order_service import OrderService
from app.config import settings


router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check API health status."""
    # Check database connectivity
    try:
        await db.execute(select(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Check Discord configuration
    discord_status = "configured" if settings.is_discord_configured else "not_configured"
    
    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
        discord=discord_status,
        timestamp=datetime.utcnow(),
    )


@router.post("/orders/sync", response_model=OrderSyncResponse)
async def sync_orders(
    request: OrderSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronize orders from the Chrome extension.
    
    This endpoint receives order data scraped from Eldorado.gg
    and updates the local database.
    """
    order_service = OrderService()
    
    return await order_service.sync_orders(
        db=db,
        orders_data=request.orders,
        timestamp=request.timestamp,
    )


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    include_filtered: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List orders with pagination and filtering."""
    query = select(Order)
    
    if status:
        query = query.where(Order.status == status)
    
    if not include_filtered:
        query = query.where(Order.is_filtered_out == False)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Order.first_seen_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific order by ID."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse.model_validate(order)


@router.get("/orders/{order_id}/events", response_model=List[OrderEventResponse])
async def get_order_events(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get events for a specific order."""
    result = await db.execute(
        select(OrderEvent)
        .where(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.occurred_at.desc())
    )
    events = result.scalars().all()
    
    return [OrderEventResponse.model_validate(e) for e in events]


# Filter Rules Endpoints
@router.get("/filters", response_model=List[FilterRuleResponse])
async def list_filters(db: AsyncSession = Depends(get_db)):
    """List all filter rules."""
    result = await db.execute(
        select(FilterRule).order_by(FilterRule.priority)
    )
    rules = result.scalars().all()
    
    return [FilterRuleResponse.model_validate(r) for r in rules]


@router.post("/filters", response_model=FilterRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    rule: FilterRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new filter rule."""
    # Convert lists to comma-separated strings for storage
    db_rule = FilterRule(
        name=rule.name,
        enabled=rule.enabled,
        min_price=rule.min_price,
        max_price=rule.max_price,
        min_current_rank=rule.min_current_rank,
        max_current_rank=rule.max_current_rank,
        min_target_rank=rule.min_target_rank,
        max_target_rank=rule.max_target_rank,
        require_duo=rule.require_duo,
        require_offline=rule.require_offline,
        require_solo=rule.require_solo,
        require_stream=rule.require_stream,
        regions=",".join(rule.regions) if rule.regions else None,
        order_types=",".join(rule.order_types) if rule.order_types else None,
        keywords=",".join(rule.keywords) if rule.keywords else None,
        exclude_keywords=",".join(rule.exclude_keywords) if rule.exclude_keywords else None,
        priority=rule.priority,
    )
    
    db.add(db_rule)
    await db.flush()
    
    return FilterRuleResponse.model_validate(db_rule)


@router.put("/filters/{rule_id}", response_model=FilterRuleResponse)
async def update_filter(
    rule_id: int,
    rule_update: FilterRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing filter rule."""
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    db_rule = result.scalar_one_or_none()
    
    if not db_rule:
        raise HTTPException(status_code=404, detail="Filter rule not found")
    
    # Update fields
    update_data = rule_update.model_dump(exclude_unset=True)
    
    # Handle list to string conversions
    if "regions" in update_data and update_data["regions"] is not None:
        update_data["regions"] = ",".join(update_data["regions"])
    if "order_types" in update_data and update_data["order_types"] is not None:
        update_data["order_types"] = ",".join(update_data["order_types"])
    if "keywords" in update_data and update_data["keywords"] is not None:
        update_data["keywords"] = ",".join(update_data["keywords"])
    if "exclude_keywords" in update_data and update_data["exclude_keywords"] is not None:
        update_data["exclude_keywords"] = ",".join(update_data["exclude_keywords"])
    
    for field, value in update_data.items():
        setattr(db_rule, field, value)
    
    await db.flush()
    
    return FilterRuleResponse.model_validate(db_rule)


@router.delete("/filters/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a filter rule."""
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    db_rule = result.scalar_one_or_none()
    
    if not db_rule:
        raise HTTPException(status_code=404, detail="Filter rule not found")
    
    await db.delete(db_rule)
    await db.flush()


# Configuration Endpoints
@router.get("/config", response_model=List[ConfigurationResponse])
async def list_config(db: AsyncSession = Depends(get_db)):
    """List all configuration entries."""
    result = await db.execute(select(Configuration).order_by(Configuration.key))
    configs = result.scalars().all()
    
    return [ConfigurationResponse.model_validate(c) for c in configs]


@router.post("/config", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config: ConfigurationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a configuration entry."""
    # Check if exists
    result = await db.execute(
        select(Configuration).where(Configuration.key == config.key)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.value = config.value
        existing.description = config.description
        existing.is_sensitive = config.is_sensitive
        db_config = existing
    else:
        db_config = Configuration(
            key=config.key,
            value=config.value,
            description=config.description,
            is_sensitive=config.is_sensitive,
        )
        db.add(db_config)
    
    await db.flush()
    
    return ConfigurationResponse.model_validate(db_config)


@router.put("/config/{config_key}", response_model=ConfigurationResponse)
async def update_config(
    config_key: str,
    config_update: ConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a configuration entry."""
    result = await db.execute(
        select(Configuration).where(Configuration.key == config_key)
    )
    db_config = result.scalar_one_or_none()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    db_config.value = config_update.value
    if config_update.description is not None:
        db_config.description = config_update.description
    
    await db.flush()
    
    return ConfigurationResponse.model_validate(db_config)


# Audit Log Endpoints
@router.get("/audit", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List recent audit log entries."""
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return [AuditLogResponse.model_validate(l) for l in logs]
