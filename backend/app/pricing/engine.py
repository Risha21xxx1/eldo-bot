"""
Pricing engine for League of Legends boosting orders.

This module provides comprehensive pricing calculations for different order types:
- RANK_BOOST: Climbing from one rank to another
- PLACEMENTS: Placement games
- NET_WINS: Net wins required

Supports global pricing, regional pricing, custom overrides, and modifiers.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import math

from app.models import LoLRank, OrderType as ModelOrderType


class OrderTypeEnum(str, Enum):
    """Order type enumeration for pricing engine."""
    RANK_BOOST = "RANK_BOOST"
    PLACEMENTS = "PLACEMENTS"
    NET_WINS = "NET_WINS"


class Division(str, Enum):
    """League divisions."""
    IV = "IV"
    III = "III"
    II = "II"
    I = "I"


class CompletionMethod(str, Enum):
    """Completion method for boosting."""
    SOLO_DUO = "Solo/Duo"
    FLEX = "Flex"


@dataclass
class RankPosition:
    """Represents a specific rank position with tier and division."""
    tier: LoLRank
    division: Optional[Division] = None
    lp: int = 0
    
    def __post_init__(self):
        # Master+ ranks don't have divisions
        if self.tier in [LoLRank.MASTER, LoLRank.GRANDMASTER, LoLRank.CHALLENGER]:
            self.division = None


@dataclass
class PricingTier:
    """Pricing configuration for a specific rank tier."""
    price_per_unit: float  # Per division, game, or win depending on order type
    hours_per_unit: float
    skip_allowed: bool = True


@dataclass
class RegionalPricing:
    """Regional pricing configuration."""
    region: str
    multiplier: float = 1.0
    price_overrides: Optional[Dict[str, PricingTier]] = None


@dataclass
class CustomPriceOverride:
    """Custom price override for specific rank transitions."""
    current_tier: LoLRank
    current_division: Optional[Division]
    target_tier: LoLRank
    target_division: Optional[Division]
    price: float
    hours: float
    region_filter: Optional[List[str]] = None
    active: bool = True


@dataclass
class Modifiers:
    """Price modifiers for order requirements."""
    duo_multiplier: float = 1.3
    offline_multiplier: float = 1.1
    solo_queue_multiplier: float = 1.15
    stream_multiplier: float = 1.15
    flex_multiplier: float = 0.9  # Flex is typically easier/cheaper


@dataclass
class PricingResult:
    """Result of a pricing calculation."""
    base_price: float
    modified_price: float
    base_hours: float
    estimated_hours: float
    divisions_crossed: int = 0
    games_count: int = 0
    wins_count: int = 0
    applied_modifiers: List[str] = field(default_factory=list)
    pricing_source: str = "global"  # global, regional, custom_override
    skip_applied: bool = False
    breakdown: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PricingConfig:
    """Complete pricing configuration."""
    # Global pricing by rank tier
    rank_boost_pricing: Dict[LoLRank, PricingTier] = field(default_factory=dict)
    placement_pricing: Dict[LoLRank, PricingTier] = field(default_factory=dict)
    net_wins_pricing: Dict[LoLRank, PricingTier] = field(default_factory=dict)
    
    # Regional pricing
    regional_pricing: Dict[str, RegionalPricing] = field(default_factory=dict)
    
    # Custom overrides (processed in order)
    custom_overrides: List[CustomPriceOverride] = field(default_factory=list)
    
    # Modifiers
    modifiers: Modifiers = field(default_factory=Modifiers)
    
    # Defaults
    default_price_per_division: float = 5.0
    default_hours_per_division: float = 2.0
    default_price_per_game: float = 8.0
    default_hours_per_game: float = 1.5
    default_price_per_win: float = 12.0
    default_hours_per_win: float = 2.0
    
    min_order_value: float = 10.0
    max_order_value: float = 500.0


class PricingEngine:
    """
    Comprehensive pricing engine for League of Legends boosting orders.
    
    Handles rank-to-rank calculations, placement games, net wins,
    regional pricing, custom overrides, and delivery time estimation.
    """
    
    # Rank order for comparisons
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
    
    DIVISION_ORDER: List[Division] = [Division.IV, Division.III, Division.II, Division.I]
    
    # Default pricing configuration
    DEFAULT_RANK_BOOST_PRICING: Dict[LoLRank, PricingTier] = {
        LoLRank.IRON: PricingTier(price_per_unit=4.0, hours_per_unit=1.5),
        LoLRank.BRONZE: PricingTier(price_per_unit=4.5, hours_per_unit=1.5),
        LoLRank.SILVER: PricingTier(price_per_unit=5.0, hours_per_unit=2.0),
        LoLRank.GOLD: PricingTier(price_per_unit=6.0, hours_per_unit=2.5),
        LoLRank.PLATINUM: PricingTier(price_per_unit=7.5, hours_per_unit=3.0),
        LoLRank.EMERALD: PricingTier(price_per_unit=9.0, hours_per_unit=3.5),
        LoLRank.DIAMOND: PricingTier(price_per_unit=12.0, hours_per_unit=4.5),
        LoLRank.MASTER: PricingTier(price_per_unit=18.0, hours_per_unit=6.0, skip_allowed=False),
        LoLRank.GRANDMASTER: PricingTier(price_per_unit=25.0, hours_per_unit=8.0, skip_allowed=False),
        LoLRank.CHALLENGER: PricingTier(price_per_unit=35.0, hours_per_unit=10.0, skip_allowed=False),
    }
    
    DEFAULT_PLACEMENT_PRICING: Dict[LoLRank, PricingTier] = {
        LoLRank.IRON: PricingTier(price_per_unit=6.0, hours_per_unit=1.5),
        LoLRank.BRONZE: PricingTier(price_per_unit=7.0, hours_per_unit=1.5),
        LoLRank.SILVER: PricingTier(price_per_unit=8.0, hours_per_unit=2.0),
        LoLRank.GOLD: PricingTier(price_per_unit=10.0, hours_per_unit=2.5),
        LoLRank.PLATINUM: PricingTier(price_per_unit=12.0, hours_per_unit=3.0),
        LoLRank.EMERALD: PricingTier(price_per_unit=15.0, hours_per_unit=3.5),
        LoLRank.DIAMOND: PricingTier(price_per_unit=20.0, hours_per_unit=4.5),
        LoLRank.MASTER: PricingTier(price_per_unit=30.0, hours_per_unit=6.0),
        LoLRank.GRANDMASTER: PricingTier(price_per_unit=40.0, hours_per_unit=8.0),
        LoLRank.CHALLENGER: PricingTier(price_per_unit=50.0, hours_per_unit=10.0),
    }
    
    DEFAULT_NET_WINS_PRICING: Dict[LoLRank, PricingTier] = {
        LoLRank.IRON: PricingTier(price_per_unit=8.0, hours_per_unit=2.0),
        LoLRank.BRONZE: PricingTier(price_per_unit=9.0, hours_per_unit=2.0),
        LoLRank.SILVER: PricingTier(price_per_unit=10.0, hours_per_unit=2.5),
        LoLRank.GOLD: PricingTier(price_per_unit=12.0, hours_per_unit=3.0),
        LoLRank.PLATINUM: PricingTier(price_per_unit=15.0, hours_per_unit=3.5),
        LoLRank.EMERALD: PricingTier(price_per_unit=18.0, hours_per_unit=4.0),
        LoLRank.DIAMOND: PricingTier(price_per_unit=25.0, hours_per_unit=5.0),
        LoLRank.MASTER: PricingTier(price_per_unit=35.0, hours_per_unit=7.0),
        LoLRank.GRANDMASTER: PricingTier(price_per_unit=50.0, hours_per_unit=9.0),
        LoLRank.CHALLENGER: PricingTier(price_per_unit=70.0, hours_per_unit=12.0),
    }
    
    DEFAULT_REGIONAL_MULTIPLIERS: Dict[str, float] = {
        "NA": 1.0,
        "EUW": 1.0,
        "EUNE": 0.95,
        "KR": 1.3,
        "BR": 0.9,
        "LAS": 0.9,
        "LAN": 0.9,
        "OCE": 1.1,
        "RU": 0.85,
        "TR": 0.85,
        "JP": 1.1,
        "VN": 0.8,
        "PH": 0.8,
        "SG": 1.0,
        "TH": 0.8,
        "TW": 1.0,
    }
    
    def __init__(self, config: Optional[PricingConfig] = None):
        """
        Initialize the pricing engine.
        
        Args:
            config: Optional pricing configuration. Uses defaults if not provided.
        """
        if config is None:
            self.config = self._create_default_config()
        else:
            self.config = config
    
    def _create_default_config(self) -> PricingConfig:
        """Create default pricing configuration."""
        return PricingConfig(
            rank_boost_pricing=self.DEFAULT_RANK_BOOST_PRICING.copy(),
            placement_pricing=self.DEFAULT_PLACEMENT_PRICING.copy(),
            net_wins_pricing=self.DEFAULT_NET_WINS_PRICING.copy(),
            regional_pricing={
                region: RegionalPricing(region=region, multiplier=mult)
                for region, mult in self.DEFAULT_REGIONAL_MULTIPLIERS.items()
            },
            modifiers=Modifiers(),
        )
    
    @staticmethod
    def get_rank_index(tier: LoLRank) -> int:
        """Get the numeric index of a rank tier."""
        try:
            return PricingEngine.RANK_ORDER.index(tier)
        except ValueError:
            return 0
    
    @staticmethod
    def get_division_index(division: Optional[Division]) -> int:
        """Get the numeric index of a division (0=IV, 3=I)."""
        if division is None:
            return 0
        try:
            return PricingEngine.DIVISION_ORDER.index(division)
        except ValueError:
            return 0
    
    @staticmethod
    def is_master_plus(tier: LoLRank) -> bool:
        """Check if rank is Master or above (no divisions)."""
        return tier in [LoLRank.MASTER, LoLRank.GRANDMASTER, LoLRank.CHALLENGER]
    
    def calculate_divisions_between(
        self,
        current_tier: LoLRank,
        current_division: Optional[Division],
        target_tier: LoLRank,
        target_division: Optional[Division],
    ) -> int:
        """
        Calculate the number of divisions between two ranks.
        
        Examples:
            Gold IV -> Gold I: 3 divisions
            Gold I -> Platinum IV: 1 division
            Emerald III -> Diamond IV: 3 divisions
            Diamond IV -> Diamond II: 2 divisions
            Diamond I -> Master: 1 division
        
        Args:
            current_tier: Current rank tier
            current_division: Current division (None for Master+)
            target_tier: Target rank tier
            target_division: Target division (None for Master+)
            
        Returns:
            Number of divisions to climb
        """
        current_rank_idx = self.get_rank_index(current_tier)
        target_rank_idx = self.get_rank_index(target_tier)
        
        if current_rank_idx > target_rank_idx:
            return 0  # Invalid: target is lower than current
        
        # Handle Master+ ranks (no divisions, count as 1 unit each)
        if self.is_master_plus(target_tier):
            # Target is Master or above
            if self.is_master_plus(current_tier):
                # Both are Master+, just return tier difference
                return max(1, target_rank_idx - current_rank_idx)
            else:
                # Current is Diamond or below, target is Master+
                # Count divisions from current to Diamond I, then 1 for Diamond I -> Master, then Master+ tiers
                div_idx = self.get_division_index(current_division)
                diamond_end_idx = self.get_rank_index(LoLRank.DIAMOND)
                
                if current_tier == LoLRank.DIAMOND:
                    # Already in Diamond, count divisions to reach Diamond I
                    # Division IV=0, III=1, II=2, I=3
                    # From IV to I = 3 divisions, from III to I = 2, from II to I = 1, from I to I = 0
                    divisions_to_diamond_i = 3 - div_idx
                    
                    # Then 1 more division to go from Diamond I to Master
                    divisions_in_current_tier = divisions_to_diamond_i + 1
                else:
                    # Divisions to reach Diamond IV, then through Diamond, then to Master
                    tiers_to_diamond = diamond_end_idx - current_rank_idx
                    divisions_to_diamond_start = tiers_to_diamond * 4
                    # From current division to end of current tier
                    divisions_in_current_tier = divisions_to_diamond_start + (4 - div_idx)
                
                # Master+ tiers beyond Master (each counts as 1)
                master_tiers = target_rank_idx - diamond_end_idx - 1
                
                return divisions_in_current_tier + master_tiers
        
        # Normal calculation for Iron-Diamond
        current_div_idx = self.get_division_index(current_division)
        target_div_idx = self.get_division_index(target_division)
        
        # Calculate total divisions from start
        current_total = (current_rank_idx * 4) + current_div_idx
        target_total = (target_rank_idx * 4) + target_div_idx
        
        return max(0, target_total - current_total)
    
    def calculate_rank_boost_price(
        self,
        current_tier: LoLRank,
        current_division: Optional[Division],
        target_tier: LoLRank,
        target_division: Optional[Division],
        region: Optional[str] = None,
        completion_method: CompletionMethod = CompletionMethod.SOLO_DUO,
        duo_required: bool = False,
        offline_mode: bool = False,
        solo_queue_only: bool = False,
        stream_required: bool = False,
    ) -> PricingResult:
        """
        Calculate price for a rank boost order.
        
        Args:
            current_tier: Current rank tier
            current_division: Current division
            target_tier: Target rank tier
            target_division: Target division
            region: Server region
            completion_method: Solo/Duo or Flex
            duo_required: Whether duo with booster is required
            offline_mode: Whether offline mode is required
            solo_queue_only: Whether only solo queue games allowed
            stream_required: Whether streaming is required
            
        Returns:
            PricingResult with price and time estimates
        """
        divisions = self.calculate_divisions_between(
            current_tier, current_division, target_tier, target_division
        )
        
        if divisions == 0:
            return PricingResult(
                base_price=0.0,
                modified_price=0.0,
                base_hours=0.0,
                estimated_hours=0.0,
                divisions_crossed=0,
                pricing_source="none",
            )
        
        # Check for custom price override first (highest priority)
        custom_price = self._find_custom_override(
            current_tier, current_division, target_tier, target_division, region
        )
        
        if custom_price is not None:
            base_price = custom_price.price * divisions
            base_hours = custom_price.hours * divisions
            pricing_source = "custom_override"
        else:
            # Check regional pricing
            regional_mult = 1.0
            if region and region in self.config.regional_pricing:
                regional_mult = self.config.regional_pricing[region].multiplier
                pricing_source = "regional"
            else:
                pricing_source = "global"
            
            # Calculate base price using tier pricing
            base_price = 0.0
            base_hours = 0.0
            
            # Get pricing for each division crossed
            current_rank_idx = self.get_rank_index(current_tier)
            current_div_idx = self.get_division_index(current_division)
            
            for i in range(divisions):
                # Determine which tier this division belongs to
                total_div = (current_rank_idx * 4) + current_div_idx + i
                tier_idx = total_div // 4
                div_idx_in_tier = total_div % 4
                
                if tier_idx >= len(self.RANK_ORDER):
                    tier_idx = len(self.RANK_ORDER) - 1
                
                tier = self.RANK_ORDER[tier_idx]
                
                # Get pricing for this tier
                tier_pricing = self.config.rank_boost_pricing.get(
                    tier,
                    PricingTier(
                        price_per_unit=self.config.default_price_per_division,
                        hours_per_unit=self.config.default_hours_per_division,
                    ),
                )
                
                base_price += tier_pricing.price_per_unit
                base_hours += tier_pricing.hours_per_unit
            
            # Apply regional multiplier
            base_price *= regional_mult
        
        # Apply modifiers
        modifiers_applied = []
        modifier_mult = 1.0
        
        if completion_method == CompletionMethod.FLEX:
            modifier_mult *= self.config.modifiers.flex_multiplier
            modifiers_applied.append("flex")
        
        if duo_required:
            modifier_mult *= self.config.modifiers.duo_multiplier
            modifiers_applied.append("duo")
        
        if offline_mode:
            modifier_mult *= self.config.modifiers.offline_multiplier
            modifiers_applied.append("offline")
        
        if solo_queue_only:
            modifier_mult *= self.config.modifiers.solo_queue_multiplier
            modifiers_applied.append("solo_queue")
        
        if stream_required:
            modifier_mult *= self.config.modifiers.stream_multiplier
            modifiers_applied.append("stream")
        
        modified_price = base_price * modifier_mult
        estimated_hours = base_hours * modifier_mult
        
        # Apply min/max constraints
        modified_price = max(modified_price, self.config.min_order_value)
        modified_price = min(modified_price, self.config.max_order_value)
        
        # Check if skip is allowed
        skip_applied = False
        highest_tier_idx = self.get_rank_index(target_tier)
        if highest_tier_idx < len(self.RANK_ORDER):
            highest_tier = self.RANK_ORDER[highest_tier_idx]
            tier_pricing = self.config.rank_boost_pricing.get(highest_tier)
            if tier_pricing and not tier_pricing.skip_allowed:
                skip_applied = False  # Cannot skip at this tier
            else:
                skip_applied = True
        
        return PricingResult(
            base_price=round(base_price, 2),
            modified_price=round(modified_price, 2),
            base_hours=round(base_hours, 2),
            estimated_hours=round(estimated_hours, 2),
            divisions_crossed=divisions,
            applied_modifiers=modifiers_applied,
            pricing_source=pricing_source,
            skip_applied=skip_applied,
            breakdown={
                "current_rank": f"{current_tier.value} {current_division.value if current_division else ''}",
                "target_rank": f"{target_tier.value} {target_division.value if target_division else ''}",
                "region": region or "global",
                "completion_method": completion_method.value,
            },
        )
    
    def calculate_placement_price(
        self,
        current_tier: LoLRank,
        num_games: int,
        region: Optional[str] = None,
        completion_method: CompletionMethod = CompletionMethod.SOLO_DUO,
        duo_required: bool = False,
        offline_mode: bool = False,
        solo_queue_only: bool = False,
        stream_required: bool = False,
    ) -> PricingResult:
        """
        Calculate price for placement games.
        
        Args:
            current_tier: Current rank tier for seeding
            num_games: Number of placement games
            region: Server region
            completion_method: Solo/Duo or Flex
            duo_required: Whether duo with booster is required
            offline_mode: Whether offline mode is required
            solo_queue_only: Whether only solo queue games allowed
            stream_required: Whether streaming is required
            
        Returns:
            PricingResult with price and time estimates
        """
        if num_games <= 0:
            return PricingResult(
                base_price=0.0,
                modified_price=0.0,
                base_hours=0.0,
                estimated_hours=0.0,
                games_count=0,
                pricing_source="none",
            )
        
        # Get pricing for current tier
        tier_pricing = self.config.placement_pricing.get(
            current_tier,
            PricingTier(
                price_per_unit=self.config.default_price_per_game,
                hours_per_unit=self.config.default_hours_per_game,
            ),
        )
        
        # Check regional pricing
        regional_mult = 1.0
        pricing_source = "global"
        if region and region in self.config.regional_pricing:
            regional_mult = self.config.regional_pricing[region].multiplier
            pricing_source = "regional"
        
        base_price = tier_pricing.price_per_unit * num_games * regional_mult
        base_hours = tier_pricing.hours_per_unit * num_games
        
        # Apply modifiers
        modifiers_applied = []
        modifier_mult = 1.0
        
        if completion_method == CompletionMethod.FLEX:
            modifier_mult *= self.config.modifiers.flex_multiplier
            modifiers_applied.append("flex")
        
        if duo_required:
            modifier_mult *= self.config.modifiers.duo_multiplier
            modifiers_applied.append("duo")
        
        if offline_mode:
            modifier_mult *= self.config.modifiers.offline_multiplier
            modifiers_applied.append("offline")
        
        if solo_queue_only:
            modifier_mult *= self.config.modifiers.solo_queue_multiplier
            modifiers_applied.append("solo_queue")
        
        if stream_required:
            modifier_mult *= self.config.modifiers.stream_multiplier
            modifiers_applied.append("stream")
        
        modified_price = base_price * modifier_mult
        estimated_hours = base_hours * modifier_mult
        
        # Apply min/max constraints
        modified_price = max(modified_price, self.config.min_order_value)
        modified_price = min(modified_price, self.config.max_order_value)
        
        return PricingResult(
            base_price=round(base_price, 2),
            modified_price=round(modified_price, 2),
            base_hours=round(base_hours, 2),
            estimated_hours=round(estimated_hours, 2),
            games_count=num_games,
            applied_modifiers=modifiers_applied,
            pricing_source=pricing_source,
            breakdown={
                "current_rank": current_tier.value,
                "num_games": num_games,
                "region": region or "global",
                "completion_method": completion_method.value,
            },
        )
    
    def calculate_net_wins_price(
        self,
        current_tier: LoLRank,
        num_wins: int,
        region: Optional[str] = None,
        completion_method: CompletionMethod = CompletionMethod.SOLO_DUO,
        duo_required: bool = False,
        offline_mode: bool = False,
        solo_queue_only: bool = False,
        stream_required: bool = False,
    ) -> PricingResult:
        """
        Calculate price for net wins order.
        
        Args:
            current_tier: Current rank tier
            num_wins: Number of net wins required
            region: Server region
            completion_method: Solo/Duo or Flex
            duo_required: Whether duo with booster is required
            offline_mode: Whether offline mode is required
            solo_queue_only: Whether only solo queue games allowed
            stream_required: Whether streaming is required
            
        Returns:
            PricingResult with price and time estimates
        """
        if num_wins <= 0:
            return PricingResult(
                base_price=0.0,
                modified_price=0.0,
                base_hours=0.0,
                estimated_hours=0.0,
                wins_count=0,
                pricing_source="none",
            )
        
        # Get pricing for current tier
        tier_pricing = self.config.net_wins_pricing.get(
            current_tier,
            PricingTier(
                price_per_unit=self.config.default_price_per_win,
                hours_per_unit=self.config.default_hours_per_win,
            ),
        )
        
        # Check regional pricing
        regional_mult = 1.0
        pricing_source = "global"
        if region and region in self.config.regional_pricing:
            regional_mult = self.config.regional_pricing[region].multiplier
            pricing_source = "regional"
        
        base_price = tier_pricing.price_per_unit * num_wins * regional_mult
        base_hours = tier_pricing.hours_per_unit * num_wins
        
        # Apply modifiers
        modifiers_applied = []
        modifier_mult = 1.0
        
        if completion_method == CompletionMethod.FLEX:
            modifier_mult *= self.config.modifiers.flex_multiplier
            modifiers_applied.append("flex")
        
        if duo_required:
            modifier_mult *= self.config.modifiers.duo_multiplier
            modifiers_applied.append("duo")
        
        if offline_mode:
            modifier_mult *= self.config.modifiers.offline_multiplier
            modifiers_applied.append("offline")
        
        if solo_queue_only:
            modifier_mult *= self.config.modifiers.solo_queue_multiplier
            modifiers_applied.append("solo_queue")
        
        if stream_required:
            modifier_mult *= self.config.modifiers.stream_multiplier
            modifiers_applied.append("stream")
        
        modified_price = base_price * modifier_mult
        estimated_hours = base_hours * modifier_mult
        
        # Apply min/max constraints
        modified_price = max(modified_price, self.config.min_order_value)
        modified_price = min(modified_price, self.config.max_order_value)
        
        return PricingResult(
            base_price=round(base_price, 2),
            modified_price=round(modified_price, 2),
            base_hours=round(base_hours, 2),
            estimated_hours=round(estimated_hours, 2),
            wins_count=num_wins,
            applied_modifiers=modifiers_applied,
            pricing_source=pricing_source,
            breakdown={
                "current_rank": current_tier.value,
                "num_wins": num_wins,
                "region": region or "global",
                "completion_method": completion_method.value,
            },
        )
    
    def _find_custom_override(
        self,
        current_tier: LoLRank,
        current_division: Optional[Division],
        target_tier: LoLRank,
        target_division: Optional[Division],
        region: Optional[str],
    ) -> Optional[CustomPriceOverride]:
        """
        Find matching custom price override.
        
        Priority order:
        1. Active region filter match
        2. No region filter (applies to all)
        
        Args:
            current_tier: Current rank tier
            current_division: Current division
            target_tier: Target rank tier
            target_division: Target division
            region: Server region
            
        Returns:
            Matching CustomPriceOverride or None
        """
        for override in self.config.custom_overrides:
            if not override.active:
                continue
            
            # Check rank match
            if override.current_tier != current_tier:
                continue
            if override.current_division != current_division:
                continue
            if override.target_tier != target_tier:
                continue
            if override.target_division != target_division:
                continue
            
            # Check region filter
            if override.region_filter is not None:
                if region is None or region not in override.region_filter:
                    continue
            
            return override
        
        return None
    
    def add_custom_override(
        self,
        current_tier: LoLRank,
        current_division: Optional[Division],
        target_tier: LoLRank,
        target_division: Optional[Division],
        price: float,
        hours: float,
        region_filter: Optional[List[str]] = None,
        active: bool = True,
    ) -> None:
        """
        Add a custom price override.
        
        Args:
            current_tier: Current rank tier
            current_division: Current division
            target_tier: Target rank tier
            target_division: Target division
            price: Price per division
            hours: Hours per division
            region_filter: Optional list of regions this applies to
            active: Whether this override is active
        """
        override = CustomPriceOverride(
            current_tier=current_tier,
            current_division=current_division,
            target_tier=target_tier,
            target_division=target_division,
            price=price,
            hours=hours,
            region_filter=region_filter,
            active=active,
        )
        self.config.custom_overrides.append(override)
    
    def calculate_delivery_time(
        self,
        result: PricingResult,
        hours_per_day: float = 8.0,
        days_per_week: int = 7,
    ) -> Dict[str, Any]:
        """
        Calculate estimated delivery time from pricing result.
        
        Args:
            result: PricingResult from a price calculation
            hours_per_day: Available boosting hours per day
            days_per_week: Days per week available for boosting
            
        Returns:
            Dictionary with delivery time estimates
        """
        estimated_hours = result.estimated_hours
        
        if estimated_hours <= 0:
            return {
                "hours": 0,
                "days": 0,
                "weeks": 0,
                "formatted": "Immediate",
            }
        
        days_needed = estimated_hours / hours_per_day
        weeks_needed = days_needed / days_per_week
        
        # Format output
        if days_needed < 1:
            formatted = f"{math.ceil(estimated_hours)} hours"
        elif weeks_needed < 1:
            formatted = f"{math.ceil(days_needed)} days"
        else:
            formatted = f"{math.ceil(weeks_needed)} weeks"
        
        return {
            "hours": round(estimated_hours, 1),
            "days": round(days_needed, 1),
            "weeks": round(weeks_needed, 1),
            "formatted": formatted,
        }
    
    def update_regional_multiplier(self, region: str, multiplier: float) -> None:
        """
        Update the regional multiplier for a specific region.
        
        Args:
            region: Region code
            multiplier: New multiplier value
        """
        if region in self.config.regional_pricing:
            self.config.regional_pricing[region].multiplier = multiplier
        else:
            self.config.regional_pricing[region] = RegionalPricing(
                region=region,
                multiplier=multiplier,
            )
    
    def update_modifier(self, modifier_name: str, value: float) -> None:
        """
        Update a price modifier.
        
        Args:
            modifier_name: Name of modifier (duo, offline, solo_queue, stream, flex)
            value: New multiplier value
        """
        valid_modifiers = {
            "duo": "duo_multiplier",
            "offline": "offline_multiplier",
            "solo_queue": "solo_queue_multiplier",
            "stream": "stream_multiplier",
            "flex": "flex_multiplier",
        }
        
        if modifier_name not in valid_modifiers:
            raise ValueError(f"Invalid modifier: {modifier_name}")
        
        attr_name = valid_modifiers[modifier_name]
        setattr(self.config.modifiers, attr_name, value)
