"""
Base Strategy Class
All trading strategies inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Provides common functionality:
    - Position tracking
    - Risk management
    - Logging
    - Order management
    """
    
    def __init__(self, client, symbol: str = "cmt_btcusdt", config: Dict = None):
        """
        Initialize strategy
        
        Args:
            client: WeexClient instance
            symbol: Trading pair
            config: Strategy-specific configuration
        """
        self.client = client
        self.symbol = symbol
        self.config = config or {}
        
        # Risk Management Defaults
        self.max_position_size = self.config.get('max_position_size', 100)  # $100 max
        self.max_leverage = self.config.get('max_leverage', 5)
        self.stop_loss_percent = self.config.get('stop_loss_percent', 2.0)
        self.take_profit_percent = self.config.get('take_profit_percent', 3.0)
        self.max_daily_loss = self.config.get('max_daily_loss', 50)  # $50 max daily loss
        
        # State tracking
        self.positions: List[Dict] = []
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.is_running = False
        
        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for strategy"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    # ==================== ABSTRACT METHODS ====================
    
    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze market conditions
        
        Returns:
            Dict with analysis results (signal, confidence, etc.)
        """
        pass
    
    @abstractmethod
    def execute(self) -> Optional[Dict]:
        """
        Execute trading logic based on analysis
        
        Returns:
            Order result if placed, None otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name"""
        pass
    
    # ==================== COMMON METHODS ====================
    
    def get_current_price(self) -> float:
        """Get current market price"""
        ticker = self.client.get_ticker(self.symbol)
        return float(ticker.get('last', 0))
    
    def get_balance(self) -> float:
        """Get available USDT balance"""
        assets = self.client.get_account_assets()
        if isinstance(assets, list):
            for asset in assets:
                if asset.get('coinName') == 'USDT':
                    return float(asset.get('available', 0))
        return 0.0
    
    def can_trade(self) -> bool:
        """Check if trading is allowed based on risk rules"""
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            self.logger.warning(f"Daily loss limit reached: ${self.daily_pnl:.2f}")
            return False
        
        # Check balance
        balance = self.get_balance()
        if balance < 10:  # Minimum $10 to trade
            self.logger.warning(f"Insufficient balance: ${balance:.2f}")
            return False
        
        return True
    
    def calculate_position_size(self, price: float) -> str:
        """
        Calculate position size based on risk parameters
        
        Args:
            price: Current asset price
            
        Returns:
            Position size as string (for API)
        """
        balance = self.get_balance()
        
        # Use max 10% of balance per trade, capped at max_position_size
        trade_value = min(balance * 0.1, self.max_position_size)
        
        # Account for leverage
        position_value = trade_value * self.max_leverage
        
        # Convert to asset quantity
        quantity = position_value / price
        
        # Round to appropriate precision (BTC = 4 decimals)
        if 'btc' in self.symbol.lower():
            quantity = round(quantity, 4)
        elif 'eth' in self.symbol.lower():
            quantity = round(quantity, 3)
        else:
            quantity = round(quantity, 2)
        
        return str(quantity)
    
    def log_trade(self, order_type: str, price: float, size: str, 
                  order_id: str = None):
        """Log trade for tracking"""
        self.total_trades += 1
        self.logger.info(
            f"📊 {order_type.upper()} | {self.symbol} | "
            f"Price: ${price:,.2f} | Size: {size} | Order: {order_id}"
        )
    
    def update_pnl(self, pnl: float):
        """Update daily P&L tracking"""
        self.daily_pnl += pnl
        if pnl > 0:
            self.winning_trades += 1
        self.logger.info(f"💰 P&L Update: ${pnl:+.2f} | Daily: ${self.daily_pnl:+.2f}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100 
                    if self.total_trades > 0 else 0)
        
        return {
            'strategy': self.get_name(),
            'symbol': self.symbol,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': f"{win_rate:.1f}%",
            'daily_pnl': f"${self.daily_pnl:+.2f}",
            'is_running': self.is_running
        }
    
    def start(self):
        """Start the strategy"""
        self.is_running = True
        self.logger.info(f"🚀 {self.get_name()} started on {self.symbol}")
    
    def stop(self):
        """Stop the strategy"""
        self.is_running = False
        self.logger.info(f"🛑 {self.get_name()} stopped")
        self.logger.info(f"📈 Final Stats: {self.get_stats()}")
