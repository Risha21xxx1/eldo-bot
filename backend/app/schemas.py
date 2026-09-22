"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# Enums matching models
class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class OrderTypeEnum(str, Enum):
    RANKED_SOLO = "Ranked Solo"
    RANKED_FLEX = "Ranked Flex"
    PLACEMENT_GAMES = "Placement Games"
    WINS = "Wins"
    GAMES = "Games"
    COACHING = "Coaching"


class LoLRankEnum(str, Enum):
    IRON = "Iron"
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"
    EMERALD = "Emerald"
    DIAMOND = "Diamond"
    MASTER = "Master"
    GRANDMASTER = "Grandmaster"
    CHALLENGER = "Challenger"


class RegionEnum(str, Enum):
    NA = "NA"
    EUW = "EUW"
    EUNE = "EUNE"
    KR = "KR"
    BR = "BR"
    LAS = "LAS"
    LAN = "LAN"
    OCE = "OCE"
    RU = "RU"
    TR = "TR"
    JP = "JP"
    VN = "VN"
    PH = "PH"
    SG = "SG"
    TH = "TH"
    TW = "TW"


class QueueTypeEnum(str, Enum):
    SOLO_DUO = "Solo/Duo"
    FLEX = "Flex"
    NORMAL_DRAFT = "Normal Draft"
    BLIND_PICK = "Blind Pick"


# Rank Info Schema
class RankInfo(BaseModel):
    tier: LoLRankEnum
    division: Optional[str] = None
    lp: Optional[int] = None


# Order Schemas
class OrderBase(BaseModel):
    """Base order schema."""
    order_type: OrderTypeEnum
    price: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    region: RegionEnum
    queue_type: QueueTypeEnum
    
    # Current rank
    current_rank_tier: LoLRankEnum
    current_rank_division: Optional[str] = None
    current_rank_lp: Optional[int] = None
    
    # Target rank
    target_rank_tier: LoLRankEnum
    target_rank_division: Optional[str] = None
    target_rank_lp: Optional[int] = None
    
    # Requirements
    duo_required: bool = False
    offline_mode: bool = False
    solo_queue_only: bool = False
    stream_required: bool = False
    
    # Game counts
    requested_wins: Optional[int] = None
    requested_games: Optional[int] = None
    
    # Buyer info
    buyer_username: str
    buyer_description: Optional[str] = None


class OrderCreate(OrderBase):
    """Schema for creating a new order."""
    id: str
    url: str = Field(min_length=1, max_length=512)


class OrderUpdate(BaseModel):
    """Schema for updating an existing order."""
    status: Optional[OrderStatusEnum] = None
    price: Optional[float] = Field(default=None, gt=0)
    duo_required: Optional[bool] = None
    offline_mode: Optional[bool] = None
    solo_queue_only: Optional[bool] = None
    stream_required: Optional[bool] = None
    notes: Optional[str] = None
    is_filtered_out: Optional[bool] = None
    filter_reason: Optional[str] = None


class OrderResponse(OrderBase):
    """Schema for order responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    url: str
    status: OrderStatusEnum
    created_at: datetime
    updated_at: datetime
    first_seen_at: datetime
    last_synced_at: Optional[datetime] = None
    notes: Optional[str] = None
    is_filtered_out: bool
    filter_reason: Optional[str] = None


class OrderListResponse(BaseModel):
    """Schema for listing orders."""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int


# Extension Sync Schemas
class OrderSyncRequest(BaseModel):
    """Schema for extension order sync requests."""
    orders: List[OrderCreate]
    timestamp: datetime


class OrderSyncResponse(BaseModel):
    """Schema for extension order sync responses."""
    processed: int
    new_orders: List[str]
    updated_orders: List[str]
    skipped_orders: List[str]


# Filter Schemas
class FilterRuleBase(BaseModel):
    """Base filter rule schema."""
    name: str = Field(min_length=1, max_length=128)
    enabled: bool = True
    
    # Price filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Rank filters
    min_current_rank: Optional[LoLRankEnum] = None
    max_current_rank: Optional[LoLRankEnum] = None
    min_target_rank: Optional[LoLRankEnum] = None
    max_target_rank: Optional[LoLRankEnum] = None
    
    # Requirement filters
    require_duo: Optional[bool] = None
    require_offline: Optional[bool] = None
    require_solo: Optional[bool] = None
    require_stream: Optional[bool] = None
    
    # Region filter
    regions: Optional[List[RegionEnum]] = None
    
    # Order type filter
    order_types: Optional[List[OrderTypeEnum]] = None
    
    # Keyword filters
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    
    priority: int = Field(default=100, ge=0, le=1000)


class FilterRuleCreate(FilterRuleBase):
    """Schema for creating a filter rule."""
    pass


class FilterRuleUpdate(BaseModel):
    """Schema for updating a filter rule."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    enabled: Optional[bool] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_current_rank: Optional[LoLRankEnum] = None
    max_current_rank: Optional[LoLRankEnum] = None
    min_target_rank: Optional[LoLRankEnum] = None
    max_target_rank: Optional[LoLRankEnum] = None
    require_duo: Optional[bool] = None
    require_offline: Optional[bool] = None
    require_solo: Optional[bool] = None
    require_stream: Optional[bool] = None
    regions: Optional[List[RegionEnum]] = None
    order_types: Optional[List[OrderTypeEnum]] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    priority: Optional[int] = Field(default=None, ge=0, le=1000)


class FilterRuleResponse(BaseModel):
    """Schema for filter rule responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    enabled: bool
    name: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_current_rank: Optional[LoLRankEnum] = None
    max_current_rank: Optional[LoLRankEnum] = None
    min_target_rank: Optional[LoLRankEnum] = None
    max_target_rank: Optional[LoLRankEnum] = None
    require_duo: Optional[bool] = None
    require_offline: Optional[bool] = None
    require_solo: Optional[bool] = None
    require_stream: Optional[bool] = None
    priority: int
    # Stored as comma-separated strings in DB
    regions: Optional[str] = None
    order_types: Optional[str] = None
    keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Configuration Schemas
class ConfigurationCreate(BaseModel):
    """Schema for creating configuration."""
    key: str = Field(min_length=1, max_length=128)
    value: str
    description: Optional[str] = None
    is_sensitive: bool = False


class ConfigurationResponse(BaseModel):
    """Schema for configuration responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    key: str
    value: str
    description: Optional[str] = None
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime


class ConfigurationUpdate(BaseModel):
    """Schema for updating configuration."""
    value: str
    description: Optional[str] = None


# Discord Schemas
class DiscordNotification(BaseModel):
    """Schema for Discord notifications."""
    webhook_url: Optional[str] = None
    title: str
    description: str
    color: int = 0x5865F2  # Discord blurple
    order_id: Optional[str] = None
    order_url: Optional[str] = None
    ping_roles: List[str] = []
    ping_users: List[str] = []


# Health Check Schema
class HealthCheckResponse(BaseModel):
    """Schema for health check responses."""
    status: str
    version: str
    database: str
    discord: str
    timestamp: datetime


# Event Schemas
class OrderEventBase(BaseModel):
    """Base order event schema."""
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class OrderEventCreate(OrderEventBase):
    """Schema for creating order events."""
    order_id: str


class OrderEventResponse(OrderEventBase):
    """Schema for order event responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_id: str
    occurred_at: datetime
    discord_sent: bool
    discord_message_id: Optional[str] = None


# Audit Log Schemas
class AuditLogResponse(BaseModel):
    """Schema for audit log responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    actor: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    occurred_at: datetime


# Generic Response
class ApiResponse(BaseModel):
    """Generic API response schema."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
