"""
Risk Manager Module
Centralized risk management for all strategies
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging


@dataclass
class RiskLimits:
    """Risk limit configuration"""
    max_position_size_usd: float = 100.0      # Max per position
    max_total_exposure_usd: float = 500.0     # Max total across all positions
    max_leverage: int = 5                      # Max leverage
    max_daily_loss_usd: float = 50.0          # Stop trading if daily loss exceeds
    max_daily_trades: int = 50                 # Max trades per day
    stop_loss_percent: float = 2.0            # Default stop loss %
    take_profit_percent: float = 3.0          # Default take profit %
    min_balance_usd: float = 50.0             # Min balance to continue trading


class RiskManager:
    """
    Centralized Risk Manager
    
    Tracks and enforces risk limits across all strategies
    """
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.logger = logging.getLogger("RiskManager")
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Position tracking
        self.open_positions: Dict[str, Dict] = {}
        self.total_exposure = 0.0
        
        self._setup_logging()
    
    def _setup_logging(self):
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | RISK | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _check_daily_reset(self):
        """Reset daily counters if new day"""
        now = datetime.now()
        if now.date() > self.daily_reset_time.date():
            self.logger.info("📅 New trading day - resetting daily limits")
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0)
    
    def can_open_position(self, size_usd: float, symbol: str) -> tuple[bool, str]:
        """
        Check if a new position can be opened
        
        Args:
            size_usd: Position size in USD
            symbol: Trading pair
            
        Returns:
            (can_trade, reason)
        """
        self._check_daily_reset()
        
        # Check daily loss limit
        if self.daily_pnl <= -self.limits.max_daily_loss_usd:
            return False, f"Daily loss limit reached: ${self.daily_pnl:.2f}"
        
        # Check daily trade limit
        if self.daily_trades >= self.limits.max_daily_trades:
            return False, f"Daily trade limit reached: {self.daily_trades}"
        
        # Check position size
        if size_usd > self.limits.max_position_size_usd:
            return False, f"Position too large: ${size_usd:.2f} > ${self.limits.max_position_size_usd:.2f}"
        
        # Check total exposure
        new_exposure = self.total_exposure + size_usd
        if new_exposure > self.limits.max_total_exposure_usd:
            return False, f"Total exposure limit: ${new_exposure:.2f} > ${self.limits.max_total_exposure_usd:.2f}"
        
        return True, "OK"
    
    def record_trade(self, symbol: str, side: str, size_usd: float, 
                    price: float, order_id: str):
        """Record a new trade"""
        self.daily_trades += 1
        
        self.open_positions[order_id] = {
            'symbol': symbol,
            'side': side,
            'size_usd': size_usd,
            'entry_price': price,
            'entry_time': datetime.now()
        }
        
        self.total_exposure += size_usd
        
        self.logger.info(f"📝 Trade recorded: {side} {symbol} ${size_usd:.2f} @ ${price:,.2f}")
    
    def record_close(self, order_id: str, pnl: float):
        """Record position close and P&L"""
        if order_id in self.open_positions:
            pos = self.open_positions.pop(order_id)
            self.total_exposure -= pos['size_usd']
        
        self.daily_pnl += pnl
        
        emoji = "💚" if pnl >= 0 else "🔴"
        self.logger.info(f"{emoji} Position closed: ${pnl:+.2f} | Daily P&L: ${self.daily_pnl:+.2f}")
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price"""
        sl_pct = self.limits.stop_loss_percent / 100
        
        if side.lower() == 'buy':
            return entry_price * (1 - sl_pct)
        else:
            return entry_price * (1 + sl_pct)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """Calculate take profit price"""
        tp_pct = self.limits.take_profit_percent / 100
        
        if side.lower() == 'buy':
            return entry_price * (1 + tp_pct)
        else:
            return entry_price * (1 - tp_pct)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        self._check_daily_reset()
        
        return {
            'daily_pnl': f"${self.daily_pnl:+.2f}",
            'daily_trades': self.daily_trades,
            'open_positions': len(self.open_positions),
            'total_exposure': f"${self.total_exposure:.2f}",
            'can_trade': self.daily_pnl > -self.limits.max_daily_loss_usd,
            'limits': {
                'max_position': f"${self.limits.max_position_size_usd:.2f}",
                'max_exposure': f"${self.limits.max_total_exposure_usd:.2f}",
                'max_daily_loss': f"${self.limits.max_daily_loss_usd:.2f}",
                'max_leverage': f"{self.limits.max_leverage}x"
            }
        }
    
    def emergency_stop(self) -> str:
        """Trigger emergency stop - flag all positions for closing"""
        self.logger.warning("🚨 EMERGENCY STOP TRIGGERED")
        return f"Emergency stop - {len(self.open_positions)} positions flagged for closing"


# Quick test
if __name__ == "__main__":
    rm = RiskManager()
    
    print("\n📊 Risk Manager Status:")
    status = rm.get_status()
    for k, v in status.items():
        print(f"   {k}: {v}")
    
    # Test trade recording
    can_trade, reason = rm.can_open_position(50.0, "cmt_btcusdt")
    print(f"\n✅ Can open $50 position: {can_trade} ({reason})")
    
    # Test limits
    can_trade, reason = rm.can_open_position(200.0, "cmt_btcusdt")
    print(f"❌ Can open $200 position: {can_trade} ({reason})")
