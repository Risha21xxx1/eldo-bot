"""
Order filtering engine.

This module provides functionality to filter orders based on
configurable rules and criteria.
"""
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, FilterRule, LoLRank, OrderType, Region


class FilterEngine:
    """
    Engine for filtering orders based on rules.
    
    Applies configurable filter rules to determine which orders
    should be shown, hidden, or flagged for review.
    """
    
    # Rank ordering for comparison
    RANK_ORDER: List[LoLRank] = [
        LoLRank.IRON,
        LoLRank.BRONZE,
        LoLRank.SILVER,
        LoLRank.GOLD,
        LoLRank.PLATINUM,
        LoLRank.EMERALD,
        LoLRank.DIAMOND,
        LoLRank.MASTER,
        LoLRank.GRANDMASTER,
        LoLRank.CHALLENGER,
    ]
    
    def __init__(self):
        """Initialize the filter engine."""
        self._rank_order_map = {rank: idx for idx, rank in enumerate(self.RANK_ORDER)}
    
    def _compare_ranks(self, rank1: LoLRank, rank2: LoLRank) -> int:
        """
        Compare two ranks.
        
        Returns:
            -1 if rank1 < rank2, 0 if equal, 1 if rank1 > rank2
        """
        idx1 = self._rank_order_map.get(rank1, 0)
        idx2 = self._rank_order_map.get(rank2, 0)
        
        if idx1 < idx2:
            return -1
        elif idx1 > idx2:
            return 1
        return 0
    
    def _rank_gte(self, rank: LoLRank, min_rank: LoLRank) -> bool:
        """Check if rank is greater than or equal to minimum rank."""
        return self._compare_ranks(rank, min_rank) >= 0
    
    def _rank_lte(self, rank: LoLRank, max_rank: LoLRank) -> bool:
        """Check if rank is less than or equal to maximum rank."""
        return self._compare_ranks(rank, max_rank) <= 0
    
    def evaluate_order_against_rule(
        self, order: Order, rule: FilterRule
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate a single order against a filter rule.
        
        Args:
            order: The order to evaluate
            rule: The filter rule to apply
            
        Returns:
            Tuple of (passes_filter, reason_if_failed)
        """
        if not rule.enabled:
            return True, None
        
        # Price filters
        if rule.min_price is not None and order.price < rule.min_price:
            return False, f"Price {order.price} below minimum {rule.min_price}"
        
        if rule.max_price is not None and order.price > rule.max_price:
            return False, f"Price {order.price} above maximum {rule.max_price}"
        
        # Current rank filters
        if rule.min_current_rank is not None:
            if not self._rank_gte(order.current_rank_tier, rule.min_current_rank):
                return False, f"Current rank below minimum {rule.min_current_rank.value}"
        
        if rule.max_current_rank is not None:
            if not self._rank_lte(order.current_rank_tier, rule.max_current_rank):
                return False, f"Current rank above maximum {rule.max_current_rank.value}"
        
        # Target rank filters
        if rule.min_target_rank is not None:
            if not self._rank_gte(order.target_rank_tier, rule.min_target_rank):
                return False, f"Target rank below minimum {rule.min_target_rank.value}"
        
        if rule.max_target_rank is not None:
            if not self._rank_lte(order.target_rank_tier, rule.max_target_rank):
                return False, f"Target rank above maximum {rule.max_target_rank.value}"
        
        # Requirement filters
        if rule.require_duo is True and not order.duo_required:
            return False, "Requires duo but order is solo"
        
        if rule.require_duo is False and order.duo_required:
            return False, "Excludes duo but order requires duo"
        
        if rule.require_offline is True and not order.offline_mode:
            return False, "Requires offline but order is online"
        
        if rule.require_offline is False and order.offline_mode:
            return False, "Excludes offline but order is offline"
        
        if rule.require_solo is True and not order.solo_queue_only:
            return False, "Requires solo queue but order allows duo"
        
        if rule.require_stream is True and not order.stream_required:
            return False, "Requires stream but order doesn't"
        
        # Region filter
        if rule.regions:
            allowed_regions = [r.strip() for r in rule.regions.split(",")]
            if order.region.value not in allowed_regions:
                return False, f"Region {order.region.value} not in allowed list"
        
        # Order type filter
        if rule.order_types:
            allowed_types = [t.strip() for t in rule.order_types.split(",")]
            if order.order_type.value not in allowed_types:
                return False, f"Order type {order.order_type.value} not in allowed list"
        
        # Keyword filters
        if rule.keywords:
            keywords = [k.strip().lower() for k in rule.keywords.split(",")]
            description = (order.buyer_description or "").lower()
            if not any(kw in description for kw in keywords):
                return False, "No matching keywords in description"
        
        # Exclude keyword filters
        if rule.exclude_keywords:
            exclude_keywords = [k.strip().lower() for k in rule.exclude_keywords.split(",")]
            description = (order.buyer_description or "").lower()
            title = (order.buyer_username or "").lower()
            if any(kw in description or kw in title for kw in exclude_keywords):
                return False, "Contains excluded keywords"
        
        return True, None
    
    async def apply_all_rules(
        self,
        db: AsyncSession,
        order: Order
    ) -> Tuple[bool, List[str]]:
        """
        Apply all enabled filter rules to an order.
        
        Args:
            db: Database session
            order: The order to evaluate
            
        Returns:
            Tuple of (passes_all_filters, list_of_failure_reasons)
        """
        # Get all enabled rules ordered by priority
        result = await db.execute(
            select(FilterRule)
            .where(FilterRule.enabled == True)
            .order_by(FilterRule.priority)
        )
        rules = result.scalars().all()
        
        failure_reasons = []
        
        for rule in rules:
            passes, reason = self.evaluate_order_against_rule(order, rule)
            if not passes and reason:
                failure_reasons.append(f"[{rule.name}] {reason}")
        
        return len(failure_reasons) == 0, failure_reasons
    
    async def filter_orders_query(
        self,
        db: AsyncSession,
        query: Any,
        include_filtered: bool = False
    ) -> Any:
        """
        Apply filters to a SQLAlchemy query.
        
        Args:
            db: Database session
            query: Base SQLAlchemy query
            include_filtered: Whether to include filtered-out orders
            
        Returns:
            Modified query with filters applied
        """
        if not include_filtered:
            query = query.where(Order.is_filtered_out == False)
        
        return query
    
    def get_rank_value(self, rank: LoLRank) -> int:
        """Get numeric value for rank comparison."""
        return self._rank_order_map.get(rank, 0)
