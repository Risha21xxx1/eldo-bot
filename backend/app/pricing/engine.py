"""
Pricing engine for evaluating order profitability.

This module provides functionality to calculate expected value
and profitability of boosting orders based on configuration.
"""
from typing import Dict, Any, Optional
from app.models import LoLRank, Order


class PricingEngine:
    """
    Engine for calculating order pricing and profitability.
    
    Uses configurable multipliers and base rates to determine
    if an order meets minimum profitability thresholds.
    """
    
    # Default rank difficulty multipliers (LP gain difficulty)
    DEFAULT_RANK_MULTIPLIERS: Dict[LoLRank, float] = {
        LoLRank.IRON: 1.0,
        LoLRank.BRONZE: 1.0,
        LoLRank.SILVER: 1.1,
        LoLRank.GOLD: 1.2,
        LoLRank.PLATINUM: 1.3,
        LoLRank.EMERALD: 1.4,
        LoLRank.DIAMOND: 1.6,
        LoLRank.MASTER: 2.0,
        LoLRank.GRANDMASTER: 2.5,
        LoLRank.CHALLENGER: 3.0,
    }
    
    # Default requirement multipliers
    DUO_MULTIPLIER = 1.3
    OFFLINE_MULTIPLIER = 1.1
    STREAM_MULTIPLIER = 1.15
    
    # Default base price per LP
    BASE_PRICE_PER_LP = 0.50  # USD
    
    # Minimum order value
    MIN_ORDER_VALUE = 10.00  # USD
    
    def __init__(
        self,
        base_price_per_lp: float = BASE_PRICE_PER_LP,
        rank_multipliers: Optional[Dict[LoLRank, float]] = None,
        duo_multiplier: float = DUO_MULTIPLIER,
        offline_multiplier: float = OFFLINE_MULTIPLIER,
        stream_multiplier: float = STREAM_MULTIPLIER,
        min_order_value: float = MIN_ORDER_VALUE,
    ):
        """
        Initialize the pricing engine.
        
        Args:
            base_price_per_lp: Base price per LP point
            rank_multipliers: Dictionary of rank tier multipliers
            duo_multiplier: Multiplier for duo queue requirements
            offline_multiplier: Multiplier for offline mode requirements
            stream_multiplier: Multiplier for stream requirements
            min_order_value: Minimum acceptable order value
        """
        self.base_price_per_lp = base_price_per_lp
        self.rank_multipliers = rank_multipliers or self.DEFAULT_RANK_MULTIPLIERS.copy()
        self.duo_multiplier = duo_multiplier
        self.offline_multiplier = offline_multiplier
        self.stream_multiplier = stream_multiplier
        self.min_order_value = min_order_value
    
    def calculate_lp_difference(self, order: Order) -> int:
        """
        Calculate the total LP difference between current and target rank.
        
        Args:
            order: The order to calculate
            
        Returns:
            Total LP difference
        """
        # Rank to LP conversion (approximate)
        rank_base_lp = {
            LoLRank.IRON: 0,
            LoLRank.BRONZE: 400,
            LoLRank.SILVER: 800,
            LoLRank.GOLD: 1200,
            LoLRank.PLATINUM: 1600,
            LoLRank.EMERALD: 2000,
            LoLRank.DIAMOND: 2400,
            LoLRank.MASTER: 2800,
            LoLRank.GRANDMASTER: 3200,
            LoLRank.CHALLENGER: 3600,
        }
        
        division_lp = {"I": 300, "II": 200, "III": 100, "IV": 0}
        
        current_total = (
            rank_base_lp.get(order.current_rank_tier, 0) +
            division_lp.get(order.current_rank_division, 0) +
            (order.current_rank_lp or 0)
        )
        
        target_total = (
            rank_base_lp.get(order.target_rank_tier, 0) +
            division_lp.get(order.target_rank_division, 0) +
            (order.target_rank_lp or 0)
        )
        
        return max(0, target_total - current_total)
    
    def calculate_expected_price(self, order: Order) -> float:
        """
        Calculate the expected/minimum price for an order.
        
        Args:
            order: The order to evaluate
            
        Returns:
            Expected minimum price in USD
        """
        lp_diff = self.calculate_lp_difference(order)
        
        # Base price from LP difference
        base_price = lp_diff * self.base_price_per_lp
        
        # Apply rank multiplier (based on highest rank involved)
        highest_rank = max(
            order.current_rank_tier,
            order.target_rank_tier,
            key=lambda r: self.rank_multipliers.get(r, 1.0)
        )
        rank_multiplier = self.rank_multipliers.get(highest_rank, 1.0)
        
        # Apply requirement multipliers
        multiplier = rank_multiplier
        
        if order.duo_required:
            multiplier *= self.duo_multiplier
        
        if order.offline_mode:
            multiplier *= self.offline_multiplier
        
        if order.stream_required:
            multiplier *= self.stream_multiplier
        
        expected_price = base_price * multiplier
        
        return max(expected_price, self.min_order_value)
    
    def evaluate_order(self, order: Order) -> Dict[str, Any]:
        """
        Evaluate an order's profitability.
        
        Args:
            order: The order to evaluate
            
        Returns:
            Dictionary with evaluation results
        """
        expected_price = self.calculate_expected_price(order)
        actual_price = order.price
        
        profit_margin = ((actual_price - expected_price) / expected_price * 100) if expected_price > 0 else 0
        
        return {
            "order_id": order.id,
            "expected_price": round(expected_price, 2),
            "actual_price": actual_price,
            "profit_margin_percent": round(profit_margin, 2),
            "is_profitable": actual_price >= expected_price,
            "meets_minimum": actual_price >= self.min_order_value,
            "lp_difference": self.calculate_lp_difference(order),
        }
    
    def is_order_worthwhile(self, order: Order, min_profit_margin: float = 0.0) -> bool:
        """
        Check if an order meets profitability criteria.
        
        Args:
            order: The order to check
            min_profit_margin: Minimum profit margin percentage required
            
        Returns:
            True if order meets criteria
        """
        evaluation = self.evaluate_order(order)
        return (
            evaluation["is_profitable"] and
            evaluation["profit_margin_percent"] >= min_profit_margin
        )
