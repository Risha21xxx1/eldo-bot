"""
Backend tests.
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus, OrderType, LoLRank, Region, QueueType
from app.schemas import OrderCreate
from app.pricing.engine import PricingEngine
from app.filters.engine import FilterEngine


class TestPricingEngine:
    """Tests for the pricing engine."""
    
    def test_calculate_lp_difference_same_rank(self):
        """Test LP calculation when ranks are the same."""
        engine = PricingEngine()
        
        # Create a mock order (simplified)
        class MockOrder:
            current_rank_tier = LoLRank.GOLD
            current_rank_division = "II"
            current_rank_lp = 50
            target_rank_tier = LoLRank.GOLD
            target_rank_division = "III"
            target_rank_lp = 0
            duo_required = False
            offline_mode = False
            stream_required = False
        
        order = MockOrder()
        lp_diff = engine.calculate_lp_difference(order)
        
        # Gold II (200 + 50 = 250) to Gold III (100 + 0 = 100)
        # This should be 0 since target is lower
        assert lp_diff == 0
    
    def test_base_price_calculation(self):
        """Test base price per LP calculation."""
        engine = PricingEngine(base_price_per_lp=0.50)
        
        class MockOrder:
            current_rank_tier = LoLRank.SILVER
            current_rank_division = "IV"
            current_rank_lp = 0
            target_rank_tier = LoLRank.SILVER
            target_rank_division = "I"
            target_rank_lp = 100
            duo_required = False
            offline_mode = False
            stream_required = False
        
        order = MockOrder()
        expected_price = engine.calculate_expected_price(order)
        
        # Silver IV (0) to Silver I (300 + 100 = 400 LP)
        # 400 * 0.50 = 200, with Silver multiplier 1.1 = 220
        assert expected_price > 0
    
    def test_duo_multiplier(self):
        """Test duo requirement multiplier."""
        engine = PricingEngine()
        
        class MockOrder:
            current_rank_tier = LoLRank.GOLD
            current_rank_division = "IV"
            current_rank_lp = 0
            target_rank_tier = LoLRank.PLATINUM
            target_rank_division = "IV"
            target_rank_lp = 0
            duo_required = True
            offline_mode = False
            stream_required = False
        
        order_with_duo = MockOrder()
        
        order_with_duo.duo_required = False
        price_without_duo = engine.calculate_expected_price(order_with_duo)
        
        order_with_duo.duo_required = True
        price_with_duo = engine.calculate_expected_price(order_with_duo)
        
        assert price_with_duo > price_without_duo


class TestFilterEngine:
    """Tests for the filter engine."""
    
    def test_rank_comparison(self):
        """Test rank comparison logic."""
        engine = FilterEngine()
        
        assert engine._rank_gte(LoLRank.GOLD, LoLRank.SILVER) is True
        assert engine._rank_gte(LoLRank.SILVER, LoLRank.GOLD) is False
        assert engine._rank_gte(LoLRank.GOLD, LoLRank.GOLD) is True
        
        assert engine._rank_lte(LoLRank.SILVER, LoLRank.GOLD) is True
        assert engine._rank_lte(LoLRank.GOLD, LoLRank.SILVER) is False
        assert engine._rank_lte(LoLRank.GOLD, LoLRank.GOLD) is True
    
    def test_rank_order_mapping(self):
        """Test that all ranks are in the order mapping."""
        engine = FilterEngine()
        
        for rank in LoLRank:
            assert rank in engine._rank_order_map
        
        # Verify ordering
        assert engine.get_rank_value(LoLRank.IRON) < engine.get_rank_value(LoLRank.CHALLENGER)


@pytest.mark.asyncio
async def test_health_check_endpoint(client):
    """Test the health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "database" in data


@pytest.fixture
def test_order_data():
    """Fixture for test order data."""
    return OrderCreate(
        id="test-order-123",
        url="https://eldorado.gg/order/test-order-123",
        order_type=OrderType.RANKED_SOLO,
        price=25.00,
        currency="USD",
        region=Region.NA,
        queue_type=QueueType.SOLO_DUO,
        current_rank_tier=LoLRank.SILVER,
        current_rank_division="II",
        current_rank_lp=50,
        target_rank_tier=LoLRank.GOLD,
        target_rank_division="III",
        target_rank_lp=0,
        duo_required=False,
        offline_mode=False,
        solo_queue_only=True,
        stream_required=False,
        requested_wins=None,
        requested_games=None,
        buyer_username="testbuyer",
        buyer_description="Fast boost please!",
    )
