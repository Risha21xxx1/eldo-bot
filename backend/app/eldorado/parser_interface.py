"""
Eldorado order parsing interfaces.

This module defines the interface for parsing Eldorado order data from the DOM.
Actual implementation will be done in the Chrome extension content scripts.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime


class EldoradoParser:
    """
    Interface for parsing Eldorado.gg order data.
    
    This is a placeholder interface. Actual parsing logic
    will be implemented in the Chrome extension content scripts
    using DOM manipulation.
    """
    
    @staticmethod
    def parse_order_id(url: str) -> Optional[str]:
        """
        Extract order ID from Eldorado URL.
        
        Args:
            url: The full Eldorado order URL
            
        Returns:
            Order ID string or None if not found
        """
        raise NotImplementedError
    
    @staticmethod
    def parse_rank(rank_text: str) -> Dict[str, Any]:
        """
        Parse rank text into tier, division, and LP.
        
        Args:
            rank_text: Raw rank text from DOM
            
        Returns:
            Dictionary with tier, division, and lp keys
        """
        raise NotImplementedError
    
    @staticmethod
    def parse_price(price_text: str) -> float:
        """
        Parse price text into numeric value.
        
        Args:
            price_text: Raw price text from DOM
            
        Returns:
            Price as float
        """
        raise NotImplementedError
    
    @staticmethod
    def parse_requirements(requirements_elements: List[Any]) -> Dict[str, bool]:
        """
        Parse requirement flags from DOM elements.
        
        Args:
            requirements_elements: List of DOM elements containing requirements
            
        Returns:
            Dictionary with duo_required, offline_mode, solo_queue_only, stream_required
        """
        raise NotImplementedError
    
    @staticmethod
    def parse_order_type(type_text: str) -> str:
        """
        Parse order type from text.
        
        Args:
            type_text: Raw order type text
            
        Returns:
            Normalized order type string
        """
        raise NotImplementedError
    
    @staticmethod
    def parse_region(region_text: str) -> str:
        """
        Parse region from text.
        
        Args:
            region_text: Raw region text
            
        Returns:
            Normalized region code
        """
        raise NotImplementedError


# CSS Selectors for Eldorado.gg (to be used by extension)
ELDORADO_SELECTORS = {
    # Order list page
    "order_list": ".orders-list, .listings-grid",
    "order_card": ".order-card, .listing-card",
    "order_link": ".order-link, .listing-link",
    
    # Order details
    "order_title": ".order-title, h1.listing-title",
    "order_price": ".price-amount, .listing-price",
    "order_currency": ".currency-symbol",
    
    # Rank information
    "current_rank": ".current-rank, .from-rank",
    "target_rank": ".target-rank, .to-rank",
    "rank_tier": ".rank-tier",
    "rank_division": ".rank-division",
    "rank_lp": ".lp-amount",
    
    # Requirements
    "requirements_container": ".requirements, .boosting-options",
    "duo_requirement": "[data-requirement='duo'], .duo-option",
    "offline_requirement": "[data-requirement='offline'], .offline-option",
    "solo_requirement": "[data-requirement='solo'], .solo-queue-option",
    "stream_requirement": "[data-requirement='stream'], .stream-option",
    
    # Game counts
    "wins_count": ".wins-count, .requested-wins",
    "games_count": ".games-count, .requested-games",
    
    # Buyer info
    "buyer_username": ".buyer-username, .customer-name",
    "buyer_description": ".order-description, .customer-notes",
    
    # Region and queue
    "region_badge": ".region-badge, .server-region",
    "queue_type": ".queue-type, .game-mode",
    
    # Status
    "order_status": ".order-status, .listing-status",
}
