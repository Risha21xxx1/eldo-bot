"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
import enum

from app.database import Base


class OrderStatus(enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class OrderType(enum.Enum):
    """Order type enumeration."""
    RANKED_SOLO = "Ranked Solo"
    RANKED_FLEX = "Ranked Flex"
    PLACEMENT_GAMES = "Placement Games"
    WINS = "Wins"
    GAMES = "Games"
    COACHING = "Coaching"


class LoLRank(enum.Enum):
    """League of Legends rank enumeration."""
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


class Region(enum.Enum):
    """Server region enumeration."""
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


class QueueType(enum.Enum):
    """Queue type enumeration."""
    SOLO_DUO = "Solo/Duo"
    FLEX = "Flex"
    NORMAL_DRAFT = "Normal Draft"
    BLIND_PICK = "Blind Pick"


class Order(Base):
    """Eldorado order model."""
    __tablename__ = "orders"
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    
    # Order details
    order_type: Mapped[OrderType] = mapped_column(SQLEnum(OrderType), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Region and queue
    region: Mapped[Region] = mapped_column(SQLEnum(Region), nullable=False)
    queue_type: Mapped[QueueType] = mapped_column(SQLEnum(QueueType), nullable=False)
    
    # Current rank
    current_rank_tier: Mapped[LoLRank] = mapped_column(SQLEnum(LoLRank), nullable=False)
    current_rank_division: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    current_rank_lp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Target rank
    target_rank_tier: Mapped[LoLRank] = mapped_column(SQLEnum(LoLRank), nullable=False)
    target_rank_division: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    target_rank_lp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Requirements
    duo_required: Mapped[bool] = mapped_column(Boolean, default=False)
    offline_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    solo_queue_only: Mapped[bool] = mapped_column(Boolean, default=False)
    stream_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Game counts
    requested_wins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requested_games: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Buyer info
    buyer_username: Mapped[str] = mapped_column(String(128), nullable=False)
    buyer_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_filtered_out: Mapped[bool] = mapped_column(Boolean, default=False)
    filter_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Relationships
    events: Mapped[List["OrderEvent"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_region", "region"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_first_seen_at", "first_seen_at"),
        Index("ix_orders_is_filtered_out", "is_filtered_out"),
    )
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, status={self.status}, price={self.price})>"


class OrderEvent(Base):
    """Order event tracking model."""
    __tablename__ = "order_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Event type
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Event data
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Discord notification status
    discord_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_message_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Relationships
    order: Mapped["Order"] = relationship(back_populates="events")
    
    __table_args__ = (
        Index("ix_order_events_order_id", "order_id"),
        Index("ix_order_events_event_type", "event_type"),
        Index("ix_order_events_occurred_at", "occurred_at"),
    )
    
    def __repr__(self) -> str:
        return f"<OrderEvent(id={self.id}, type={self.event_type}, order={self.order_id})>"


class FilterRule(Base):
    """Filter rule configuration model."""
    __tablename__ = "filter_rules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Price filters
    min_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Rank filters
    min_current_rank: Mapped[Optional[LoLRank]] = mapped_column(SQLEnum(LoLRank), nullable=True)
    max_current_rank: Mapped[Optional[LoLRank]] = mapped_column(SQLEnum(LoLRank), nullable=True)
    min_target_rank: Mapped[Optional[LoLRank]] = mapped_column(SQLEnum(LoLRank), nullable=True)
    max_target_rank: Mapped[Optional[LoLRank]] = mapped_column(SQLEnum(LoLRank), nullable=True)
    
    # Requirement filters
    require_duo: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    require_offline: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    require_solo: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    require_stream: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Region filter (stored as comma-separated string)
    regions: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Order type filter (stored as comma-separated string)
    order_types: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Keyword filters
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exclude_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_filter_rules_enabled", "enabled"),
        Index("ix_filter_rules_priority", "priority"),
    )
    
    def __repr__(self) -> str:
        return f"<FilterRule(name={self.name}, enabled={self.enabled})>"


class Configuration(Base):
    """Application configuration storage model."""
    __tablename__ = "configurations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_configurations_key", "key"),
    )
    
    def __repr__(self) -> str:
        return f"<Configuration(key={self.key})>"


class AuditLog(Base):
    """Audit log for tracking system actions."""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Action details
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Actor (system, user, extension)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    
    # Details
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Result
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_occurred_at", "occurred_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action})>"
