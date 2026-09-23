"""
Discord notification service.

This module provides functionality to send notifications
to Discord webhooks.
"""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.config import Settings


logger = logging.getLogger(__name__)


class DiscordNotificationService:
    """
    Service for sending notifications to Discord via webhooks.
    
    Supports rich embeds, mentions, and various notification types.
    """
    
    # Color constants (decimal)
    COLOR_SUCCESS = 0x57F287  # Green
    COLOR_INFO = 0x5865F2     # Blurple
    COLOR_WARNING = 0xFEE75C  # Yellow
    COLOR_ERROR = 0xED4245    # Red
    COLOR_NEW_ORDER = 0x5865F2  # Blurple
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize the Discord notification service.
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def is_configured(self) -> bool:
        """Check if Discord is configured."""
        return self.webhook_url is not None and len(self.webhook_url) > 0
    
    async def send_notification(
        self,
        title: str,
        description: str,
        color: int = COLOR_INFO,
        order_id: Optional[str] = None,
        order_url: Optional[str] = None,
        ping_roles: Optional[List[str]] = None,
        ping_users: Optional[List[str]] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """
        Send a notification to Discord.
        
        Args:
            title: Notification title
            description: Notification description
            color: Embed color (decimal)
            order_id: Optional order ID
            order_url: Optional order URL
            ping_roles: List of role IDs to ping
            ping_users: List of user IDs to ping
            fields: Optional list of embed fields
            thumbnail_url: Optional thumbnail image URL
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_configured():
            logger.warning("Discord webhook not configured, skipping notification")
            return False
        
        # Build content with pings
        content_parts = []
        
        if ping_roles:
            for role_id in ping_roles:
                content_parts.append(f"<@&{role_id}>")
        
        if ping_users:
            for user_id in ping_users:
                content_parts.append(f"<@{user_id}>")
        
        content = " ".join(content_parts) if content_parts else None
        
        # Build embed
        embed: Dict[str, Any] = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if order_url:
            embed["url"] = order_url
        
        if fields:
            embed["fields"] = fields
        
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        
        # Add footer
        embed["footer"] = {
            "text": "Eldorado Boosting Assistant",
        }
        
        if order_id:
            embed["footer"]["text"] += f" | Order: {order_id}"
        
        payload = {
            "embeds": [embed],
        }
        
        if content:
            payload["content"] = content
        
        try:
            client = await self._get_client()
            response = await client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Discord notification sent: {title}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord notification: {e}")
            return False
    
    async def send_new_order_notification(
        self,
        order_id: str,
        order_url: str,
        price: float,
        current_rank: str,
        target_rank: str,
        region: str,
        requirements: List[str],
    ) -> bool:
        """
        Send a new order notification.
        
        Args:
            order_id: Order ID
            order_url: Order URL
            price: Order price
            current_rank: Current rank string
            target_rank: Target rank string
            region: Server region
            requirements: List of requirements
            
        Returns:
            True if notification was sent successfully
        """
        fields = [
            {"name": "Price", "value": f"${price:.2f}", "inline": True},
            {"name": "Region", "value": region, "inline": True},
            {"name": "Rank", "value": f"{current_rank} → {target_rank}", "inline": False},
        ]
        
        if requirements:
            fields.append({
                "name": "Requirements",
                "value": "\n".join(f"• {r}" for r in requirements),
                "inline": False,
            })
        
        return await self.send_notification(
            title="🎮 New Boosting Order Available",
            description=f"A new League of Legends boosting order has been detected.",
            color=self.COLOR_NEW_ORDER,
            order_id=order_id,
            order_url=order_url,
            fields=fields,
        )
    
    async def send_order_update_notification(
        self,
        order_id: str,
        order_url: str,
        change_type: str,
        old_value: str,
        new_value: str,
    ) -> bool:
        """
        Send an order update notification.
        
        Args:
            order_id: Order ID
            order_url: Order URL
            change_type: Type of change (status, price, etc.)
            old_value: Previous value
            new_value: New value
            
        Returns:
            True if notification was sent successfully
        """
        return await self.send_notification(
            title=f"📝 Order Update: {change_type}",
            description=f"Order **{order_id}** has been updated.\n\n**{change_type}:** {old_value} → {new_value}",
            color=self.COLOR_INFO,
            order_id=order_id,
            order_url=order_url,
        )
    
    async def send_error_notification(
        self,
        error_message: str,
        context: Optional[str] = None,
    ) -> bool:
        """
        Send an error notification.
        
        Args:
            error_message: Error message
            context: Optional context information
            
        Returns:
            True if notification was sent successfully
        """
        description = f"```\n{error_message}\n```"
        
        if context:
            description += f"\n\n**Context:** {context}"
        
        return await self.send_notification(
            title="❌ System Error",
            description=description,
            color=self.COLOR_ERROR,
        )
