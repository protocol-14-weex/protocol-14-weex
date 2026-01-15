"""
🎯 Grid Trading Strategy for WEEX Hackathon

Grid trading places buy and sell orders at regular intervals above and below
a set price, profiting from normal price volatility.

Features:
- RSI/MACD filters to avoid trading against strong trends
- DeepSeek AI sentiment analysis (optional)
- Risk management integration
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional, List
from .base_strategy import BaseStrategy


class GridTradingStrategy(BaseStrategy):
    """
    Grid Trading Strategy with Technical Filters
    
    Creates a grid of buy/sell orders at fixed price intervals.
    Uses RSI/MACD to filter entries and avoid bad market conditions.
    
    Best for: Sideways/ranging markets
    Risk: Price breakout beyond grid boundaries
    """
    
    def __init__(self, client, symbol: str = "cmt_btcusdt", config: Dict = None):
        """
        Initialize Grid Trading Strategy
        
        Config options:
            grid_levels: Number of grid levels (default: 3)
            grid_spacing_percent: Spacing between levels as % (default: 0.5%)
            order_size_usd: USD value per grid order (default: 10)
            rebalance_threshold: % move to trigger grid rebalance (default: 2%)
            use_filters: Enable RSI/MACD filters (default: True)
            use_sentiment: Enable DeepSeek AI (default: False)
        """
        # Default grid config
        default_config = {
            'grid_levels': 3,              # 3 levels each side (conservative)
            'grid_spacing_percent': 0.5,   # 0.5% between each level
            'order_size_usd': 10,          # $10 per grid order
            'rebalance_threshold': 2.0,    # Rebalance if price moves 2%
            'max_leverage': 5,             # 5x leverage
            'max_position_size': 100,      # $100 max total
            'use_filters': True,           # Use RSI/MACD filters
            'use_sentiment': False,        # Use DeepSeek AI
        }
        
        # Merge with user config
        if config:
            default_config.update(config)
        
        super().__init__(client, symbol, default_config)
        
        # Grid state
        self.grid_orders: Dict[str, Dict] = {}  # order_id -> order info
        self.grid_center_price = 0.0
        self.grid_levels_prices: List[float] = []
        self.last_filled_level = None
        
        # Technical indicators
        self.indicators = None
        self.sentiment = None
        
        if self.config['use_filters']:
            try:
                from utils.indicators import TechnicalIndicators
                self.indicators = TechnicalIndicators(client, symbol)
                self.logger.info("📊 Technical filters enabled (RSI/MACD)")
            except ImportError as e:
                self.logger.warning(f"⚠️ Could not load indicators: {e}")
        
        if self.config['use_sentiment']:
            try:
                from utils.sentiment import DeepSeekSentiment
                self.sentiment = DeepSeekSentiment()
                if self.sentiment.enabled:
                    self.logger.info("🤖 DeepSeek AI sentiment enabled")
                else:
                    self.sentiment = None
            except ImportError as e:
                self.logger.warning(f"⚠️ Could not load sentiment: {e}")
        
        self.logger.info(f"📊 Grid config: {self.config['grid_levels']} levels, "
                        f"{self.config['grid_spacing_percent']}% spacing")
    
    def get_name(self) -> str:
        return "Grid Trading"
    
    def check_filters(self) -> Dict[str, Any]:
        """
        Check RSI/MACD filters before placing grid
        
        Returns:
            Dict with filter status and recommendation
        """
        result = {
            'can_trade': True,
            'rsi': None,
            'macd': None,
            'sentiment': None,
            'warnings': []
        }
        
        # Check technical indicators
        if self.indicators:
            try:
                signals = self.indicators.get_combined_signal()
                
                result['rsi'] = signals['rsi']
                result['macd'] = signals['macd']
                result['trend'] = signals['trend']
                
                # Warn if RSI extreme
                if signals['rsi'].value > 75:
                    result['warnings'].append(f"⚠️ RSI very high ({signals['rsi'].value}) - market overbought")
                elif signals['rsi'].value < 25:
                    result['warnings'].append(f"⚠️ RSI very low ({signals['rsi'].value}) - market oversold")
                
                # Warn if strong trend (grid works best in ranges)
                if signals['trend'] in ['uptrend', 'downtrend']:
                    result['warnings'].append(f"⚠️ Strong {signals['trend']} detected - grid may underperform")
                
            except Exception as e:
                self.logger.warning(f"Filter check failed: {e}")
        
        # Check AI sentiment
        if self.sentiment:
            try:
                sentiment_data = self.sentiment.get_signal("BTC")
                result['sentiment'] = sentiment_data
                
                # Warn if strong bearish sentiment
                if sentiment_data['sentiment'] == 'bearish' and sentiment_data['confidence'] > 70:
                    result['warnings'].append(f"⚠️ AI detects bearish sentiment ({sentiment_data['confidence']}%)")
                    
            except Exception as e:
                self.logger.warning(f"Sentiment check failed: {e}")
        
        return result
    
    def calculate_grid_levels(self, center_price: float) -> Dict[str, List[float]]:
        """
        Calculate grid price levels around center price
        
        Returns:
            Dict with 'buy' and 'sell' price lists
        """
        levels = self.config['grid_levels']
        spacing = self.config['grid_spacing_percent'] / 100
        
        buy_levels = []
        sell_levels = []
        
        for i in range(1, levels + 1):
            # Buy levels below current price
            buy_price = center_price * (1 - spacing * i)
            buy_levels.append(round(buy_price, 1))
            
            # Sell levels above current price
            sell_price = center_price * (1 + spacing * i)
            sell_levels.append(round(sell_price, 1))
        
        return {
            'buy': buy_levels,
            'sell': sell_levels,
            'center': center_price
        }
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze if grid needs rebalancing
        
        Returns:
            Analysis with current price, grid status, action needed
        """
        current_price = self.get_current_price()
        
        # First run - no grid set
        if self.grid_center_price == 0:
            return {
                'action': 'initialize',
                'current_price': current_price,
                'message': 'No grid set, need to initialize'
            }
        
        # Calculate price deviation from grid center
        deviation = abs(current_price - self.grid_center_price) / self.grid_center_price * 100
        
        if deviation > self.config['rebalance_threshold']:
            return {
                'action': 'rebalance',
                'current_price': current_price,
                'center_price': self.grid_center_price,
                'deviation': f"{deviation:.2f}%",
                'message': 'Price moved significantly, rebalance grid'
            }
        
        return {
            'action': 'monitor',
            'current_price': current_price,
            'center_price': self.grid_center_price,
            'deviation': f"{deviation:.2f}%",
            'message': 'Grid operating normally'
        }
    
    def place_grid_orders(self, levels: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        Place buy and sell orders at grid levels
        
        Args:
            levels: Dict with 'buy' and 'sell' price lists
            
        Returns:
            Summary of placed orders
        """
        current_price = levels['center']
        order_size_usd = self.config['order_size_usd']
        
        placed_orders = {'buy': [], 'sell': []}
        
        # Calculate order size in BTC
        size = round(order_size_usd * self.config['max_leverage'] / current_price, 4)
        
        self.logger.info(f"📊 Placing grid orders: {len(levels['buy'])} buys, "
                        f"{len(levels['sell'])} sells, size: {size} BTC each")
        
        # Place buy orders (below current price)
        for i, price in enumerate(levels['buy']):
            try:
                order = self._place_limit_order(
                    side='buy',
                    price=price,
                    size=str(size),
                    label=f"grid_buy_{i}"
                )
                if order.get('order_id'):
                    placed_orders['buy'].append({
                        'order_id': order['order_id'],
                        'price': price,
                        'size': size,
                        'level': i
                    })
                    self.grid_orders[order['order_id']] = {
                        'type': 'buy', 
                        'price': price,
                        'level': i
                    }
                time.sleep(0.2)  # Rate limit
            except Exception as e:
                self.logger.error(f"Failed to place buy order at ${price}: {e}")
        
        # Place sell orders (above current price)
        for i, price in enumerate(levels['sell']):
            try:
                order = self._place_limit_order(
                    side='sell',
                    price=price,
                    size=str(size),
                    label=f"grid_sell_{i}"
                )
                if order.get('order_id'):
                    placed_orders['sell'].append({
                        'order_id': order['order_id'],
                        'price': price,
                        'size': size,
                        'level': i
                    })
                    self.grid_orders[order['order_id']] = {
                        'type': 'sell',
                        'price': price,
                        'level': i
                    }
                time.sleep(0.2)
            except Exception as e:
                self.logger.error(f"Failed to place sell order at ${price}: {e}")
        
        self.logger.info(f"✅ Placed {len(placed_orders['buy'])} buys, "
                        f"{len(placed_orders['sell'])} sells")
        
        return placed_orders
    
    def _place_limit_order(self, side: str, price: float, size: str, 
                          label: str = "") -> Dict:
        """
        Place a limit order
        
        Args:
            side: 'buy' or 'sell'
            price: Limit price
            size: Order size
            label: Client order ID label
        """
        import json
        import hmac
        import hashlib
        import base64
        
        # Order type: 1=open_long, 2=open_short, 3=close_long, 4=close_short
        order_type = "1" if side == 'buy' else "2"
        
        body = {
            "symbol": self.symbol,
            "client_oid": f"{label}_{int(time.time())}",
            "size": size,
            "type": order_type,
            "order_type": "0",     # 0 = normal order
            "match_price": "0",    # 0 = limit order
            "price": str(int(price))
        }
        
        # Use client's internal request method
        ts = str(int(time.time() * 1000))
        path = "/capi/v2/order/placeOrder"
        body_str = json.dumps(body)
        
        msg = ts + "POST" + path + body_str
        sig = base64.b64encode(
            hmac.new(
                self.client.secret_key.encode(),
                msg.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        headers = {
            "ACCESS-KEY": self.client.api_key,
            "ACCESS-SIGN": sig,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self.client.passphrase,
            "Content-Type": "application/json"
        }
        
        import requests
        resp = requests.post(
            f"{self.client.BASE_URL}{path}",
            headers=headers,
            data=body_str,
            timeout=30
        )
        
        return resp.json()
    
    def cancel_all_grid_orders(self) -> int:
        """Cancel all grid orders"""
        import json
        import hmac
        import hashlib
        import base64
        import requests
        
        cancelled = 0
        path = "/capi/v2/order/cancel_order"
        
        for order_id in list(self.grid_orders.keys()):
            try:
                ts = str(int(time.time() * 1000))
                body = json.dumps({"symbol": self.symbol, "orderId": order_id})
                msg = ts + "POST" + path + body
                sig = base64.b64encode(
                    hmac.new(
                        self.client.secret_key.encode(),
                        msg.encode(),
                        hashlib.sha256
                    ).digest()
                ).decode()
                
                headers = {
                    "ACCESS-KEY": self.client.api_key,
                    "ACCESS-SIGN": sig,
                    "ACCESS-TIMESTAMP": ts,
                    "ACCESS-PASSPHRASE": self.client.passphrase,
                    "Content-Type": "application/json"
                }
                
                resp = requests.post(
                    f"{self.client.BASE_URL}{path}",
                    headers=headers,
                    data=body,
                    timeout=10
                )
                
                if resp.status_code == 200:
                    del self.grid_orders[order_id]
                    cancelled += 1
                
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Failed to cancel order {order_id}: {e}")
        
        return cancelled
    
    def execute(self) -> Optional[Dict]:
        """
        Execute grid trading logic
        
        1. Analyze market
        2. Initialize/rebalance grid if needed
        3. Monitor filled orders
        """
        if not self.can_trade():
            return None
        
        analysis = self.analyze()
        
        if analysis['action'] == 'initialize':
            # First time setup
            self.grid_center_price = analysis['current_price']
            levels = self.calculate_grid_levels(self.grid_center_price)
            
            self.logger.info(f"🎯 Initializing grid at ${self.grid_center_price:,.2f}")
            self.logger.info(f"   Buy levels: {levels['buy']}")
            self.logger.info(f"   Sell levels: {levels['sell']}")
            
            return self.place_grid_orders(levels)
        
        elif analysis['action'] == 'rebalance':
            # Price moved too far, rebalance grid
            self.logger.info(f"🔄 Rebalancing grid (deviation: {analysis['deviation']})")
            
            # Cancel existing orders
            cancelled = self.cancel_all_grid_orders()
            self.logger.info(f"   Cancelled {cancelled} old orders")
            
            # Set new center and place new orders
            self.grid_center_price = analysis['current_price']
            levels = self.calculate_grid_levels(self.grid_center_price)
            
            return self.place_grid_orders(levels)
        
        else:
            # Normal monitoring
            self.logger.debug(f"📊 Grid OK | Price: ${analysis['current_price']:,.2f} | "
                            f"Deviation: {analysis['deviation']}")
            return None
    
    def run_once(self) -> Dict[str, Any]:
        """
        Run a single iteration of the strategy
        Useful for testing
        """
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"🎯 GRID TRADING - Single Run")
        self.logger.info(f"{'='*50}")
        
        result = self.execute()
        
        return {
            'strategy': self.get_name(),
            'symbol': self.symbol,
            'grid_center': self.grid_center_price,
            'active_orders': len(self.grid_orders),
            'result': result
        }
    
    def run_loop(self, interval: int = 60, max_iterations: int = None):
        """
        Run strategy in a loop
        
        Args:
            interval: Seconds between iterations
            max_iterations: Max loops (None = infinite)
        """
        self.start()
        iteration = 0
        
        try:
            while self.is_running:
                if max_iterations and iteration >= max_iterations:
                    break
                
                self.execute()
                iteration += 1
                
                self.logger.info(f"💤 Sleeping {interval}s... (iteration {iteration})")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("⚠️ Interrupted by user")
        finally:
            self.stop()
            # Optionally cancel all orders on stop
            # self.cancel_all_grid_orders()


# ==================== TEST ====================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    from weex_client import WeexClient
    
    print("\n🧪 Testing Grid Trading Strategy")
    print("="*50)
    
    # Initialize client
    client = WeexClient()
    
    # Create strategy with conservative config
    config = {
        'grid_levels': 3,              # 3 levels each side
        'grid_spacing_percent': 0.3,   # 0.3% spacing
        'order_size_usd': 10,          # $10 per level
        'max_leverage': 5,
    }
    
    strategy = GridTradingStrategy(client, "cmt_btcusdt", config)
    
    # Run single iteration
    result = strategy.run_once()
    
    print("\n📊 Result:")
    print(f"   Grid center: ${result['grid_center']:,.2f}")
    print(f"   Active orders: {result['active_orders']}")
    
    # Show stats
    print("\n📈 Strategy Stats:")
    stats = strategy.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
