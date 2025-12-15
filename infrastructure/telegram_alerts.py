# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Telegram Alerting System
Real-time alerts for trading events and system status.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger("godbrain.alerts")


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "ℹ️"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🚨"
    TRADE = "📈"
    DNA = "🧬"
    MONEY = "💰"


@dataclass
class Alert:
    """Alert message."""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def format_telegram(self) -> str:
        """Format for Telegram message."""
        return (
            f"{self.level.value} *{self.title}*\n"
            f"_{self.timestamp.strftime('%H:%M:%S')}_\n\n"
            f"{self.message}"
        )


class TelegramAlerter:
    """
    Telegram alert system for GODBRAIN.
    
    Sends real-time alerts for:
    - Trade executions
    - System errors
    - DNA evolution events
    - Equity milestones
    - Health check failures
    
    Usage:
        alerter = TelegramAlerter()
        await alerter.send_trade("BUY", "DOGE", 100, 0.32)
        await alerter.send_error("Connection timeout")
    """
    
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"
    
    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        self.token = token or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self._enabled = bool(self.token and self.chat_id)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self._last_alert_time: Dict[str, datetime] = {}
        self._min_interval_seconds = 5  # Min 5 seconds between same alerts
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def send(self, alert: Alert) -> bool:
        """
        Send an alert to Telegram.
        
        Returns True if sent successfully.
        """
        if not self._enabled:
            logger.warning("Telegram not configured - alert not sent")
            return False
        
        # Rate limit check
        alert_key = f"{alert.level.name}:{alert.title}"
        if alert_key in self._last_alert_time:
            elapsed = (datetime.now() - self._last_alert_time[alert_key]).total_seconds()
            if elapsed < self._min_interval_seconds:
                return False
        
        self._last_alert_time[alert_key] = datetime.now()
        
        try:
            session = await self._get_session()
            
            payload = {
                "chat_id": self.chat_id,
                "text": alert.format_telegram(),
                "parse_mode": "Markdown",
                "disable_notification": alert.level == AlertLevel.INFO
            }
            
            url = self.API_URL.format(token=self.token)
            
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.debug(f"Alert sent: {alert.title}")
                    return True
                else:
                    logger.error(f"Telegram API error: {resp.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def send_trade(
        self,
        action: str,
        symbol: str,
        size_usd: float,
        price: float,
        pnl: Optional[float] = None
    ) -> bool:
        """Send trade execution alert."""
        emoji = "🟢" if action.upper() == "BUY" else "🔴"
        pnl_str = f"\nPnL: ${pnl:+.2f}" if pnl is not None else ""
        
        alert = Alert(
            level=AlertLevel.TRADE,
            title=f"{emoji} {action.upper()} {symbol}",
            message=(
                f"Size: ${size_usd:.2f}\n"
                f"Price: ${price:.4f}"
                f"{pnl_str}"
            )
        )
        return await self.send(alert)
    
    async def send_equity_update(
        self,
        equity: float,
        change_pct: float,
        pnl_today: float
    ) -> bool:
        """Send equity milestone alert."""
        emoji = "📈" if change_pct >= 0 else "📉"
        
        alert = Alert(
            level=AlertLevel.MONEY,
            title=f"{emoji} Equity Update",
            message=(
                f"Equity: ${equity:.2f}\n"
                f"Change: {change_pct:+.2f}%\n"
                f"PnL Today: ${pnl_today:+.2f}"
            )
        )
        return await self.send(alert)
    
    async def send_dna_evolution(
        self,
        generation: int,
        fitness: float,
        dna: List[int],
        improvement: float
    ) -> bool:
        """Send DNA evolution alert."""
        alert = Alert(
            level=AlertLevel.DNA,
            title=f"DNA Generation {generation}",
            message=(
                f"Fitness: {fitness:.4f}\n"
                f"Improvement: {improvement:+.2f}%\n"
                f"DNA: `{dna[:6]}`"
            )
        )
        return await self.send(alert)
    
    async def send_error(self, error: str, component: str = "System") -> bool:
        """Send error alert."""
        alert = Alert(
            level=AlertLevel.ERROR,
            title=f"Error in {component}",
            message=error[:500]  # Truncate long errors
        )
        return await self.send(alert)
    
    async def send_critical(self, message: str, component: str = "System") -> bool:
        """Send critical alert."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            title=f"CRITICAL: {component}",
            message=message
        )
        return await self.send(alert)
    
    async def send_startup(self) -> bool:
        """Send system startup alert."""
        alert = Alert(
            level=AlertLevel.SUCCESS,
            title="GODBRAIN Started",
            message="System is online and trading."
        )
        return await self.send(alert)
    
    async def send_shutdown(self, reason: str = "Manual") -> bool:
        """Send system shutdown alert."""
        alert = Alert(
            level=AlertLevel.WARNING,
            title="GODBRAIN Stopping",
            message=f"Reason: {reason}"
        )
        return await self.send(alert)
    
    async def send_health_report(
        self,
        components: Dict[str, bool],
        equity: float,
        open_positions: int
    ) -> bool:
        """Send periodic health report."""
        status_lines = []
        for name, healthy in components.items():
            emoji = "✅" if healthy else "❌"
            status_lines.append(f"{emoji} {name}")
        
        alert = Alert(
            level=AlertLevel.INFO,
            title="Health Report",
            message=(
                f"Equity: ${equity:.2f}\n"
                f"Positions: {open_positions}\n\n"
                + "\n".join(status_lines)
            )
        )
        return await self.send(alert)
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global instance
_alerter: Optional[TelegramAlerter] = None


def get_alerter() -> TelegramAlerter:
    """Get or create global alerter instance."""
    global _alerter
    if _alerter is None:
        _alerter = TelegramAlerter()
    return _alerter


# Sync wrapper for use in non-async code
def send_alert_sync(alert: Alert) -> bool:
    """Synchronous alert sender."""
    alerter = get_alerter()
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(alerter.send(alert))
    finally:
        loop.close()


if __name__ == "__main__":
    import asyncio
    
    async def demo():
        alerter = TelegramAlerter()
        
        if not alerter._enabled:
            print("Telegram not configured. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID")
            return
        
        print("Sending test alerts...")
        
        await alerter.send_startup()
        await asyncio.sleep(1)
        
        await alerter.send_trade("BUY", "DOGE/USDT", 500, 0.32145)
        await asyncio.sleep(1)
        
        await alerter.send_equity_update(10500, 2.5, 250)
        await asyncio.sleep(1)
        
        await alerter.send_dna_evolution(42, 0.85, [10, 10, 242, 331], 5.2)
        
        await alerter.close()
        print("Done!")
    
    asyncio.run(demo())
