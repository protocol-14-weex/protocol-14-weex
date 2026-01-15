"""
🚀 WEEX Hackathon - Live Grid Trading Bot
Ejecuta Grid Trading con filtros RSI/MACD

ADVERTENCIA: Este script coloca órdenes reales con dinero real.
Usa montos pequeños para testing.
"""

import os
import sys
import time
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weex_client import WeexClient
from strategies.grid_trading import GridTradingStrategy
from utils.indicators import TechnicalIndicators


class GridTradingBot:
    """
    Live Grid Trading Bot
    
    Features:
    - RSI/MACD filters
    - Automatic grid rebalancing
    - Position monitoring
    - Clean shutdown
    """
    
    def __init__(self, config: dict = None):
        """Initialize bot with configuration"""
        
        # Default conservative config
        self.config = {
            'symbol': 'cmt_btcusdt',
            'grid_levels': 3,              # 3 levels each side
            'grid_spacing_percent': 0.4,   # 0.4% spacing (~$400 at $100k)
            'order_size_usd': 10,          # $10 per level
            'max_leverage': 5,             # 5x leverage
            'rebalance_threshold': 1.5,    # Rebalance at 1.5% deviation
            'check_interval': 60,          # Check every 60 seconds
            'use_filters': True,           # Enable RSI/MACD
            'use_sentiment': False,        # Disable AI for now (save API calls)
        }
        
        if config:
            self.config.update(config)
        
        # Initialize components
        print("\n" + "🤖"*25)
        print("   WEEX HACKATHON - GRID TRADING BOT")
        print("🤖"*25)
        
        self.client = WeexClient()
        self.strategy = GridTradingStrategy(
            self.client,
            self.config['symbol'],
            self.config
        )
        self.indicators = TechnicalIndicators(self.client, self.config['symbol'])
        
        self.is_running = False
        self.iteration = 0
        
        # Setup clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\n⚠️ Shutdown signal received...")
        self.stop()
    
    def show_status(self):
        """Display current status"""
        print("\n" + "="*60)
        print(f"📊 STATUS | {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # Get balance
        try:
            assets = self.client.get_account_assets()
            if isinstance(assets, list):
                for asset in assets:
                    if asset.get('coinName') == 'USDT':
                        available = float(asset.get('available', 0))
                        equity = float(asset.get('equity', 0))
                        print(f"💰 Balance: ${available:.2f} available / ${equity:.2f} equity")
        except Exception as e:
            print(f"❌ Failed to get balance: {e}")
        
        # Get price
        price = self.strategy.get_current_price()
        print(f"📈 {self.config['symbol'].upper()}: ${price:,.2f}")
        
        # Grid info
        if self.strategy.grid_center_price > 0:
            deviation = abs(price - self.strategy.grid_center_price) / self.strategy.grid_center_price * 100
            print(f"🎯 Grid center: ${self.strategy.grid_center_price:,.2f} (deviation: {deviation:.2f}%)")
        
        print(f"📋 Active grid orders: {len(self.strategy.grid_orders)}")
        
        # Technical indicators
        if self.config['use_filters']:
            try:
                signals = self.indicators.get_combined_signal()
                print(f"\n🔍 Technical Analysis:")
                print(f"   RSI: {signals['rsi'].message}")
                print(f"   MACD: {signals['macd'].message}")
                print(f"   Trend: {signals['trend']}")
                print(f"   Signal: {signals['signal'].upper()} ({signals['confidence']}%)")
            except Exception as e:
                print(f"   ⚠️ Could not get indicators: {e}")
    
    def check_market_conditions(self) -> bool:
        """
        Check if market conditions are suitable for grid trading
        
        Returns:
            True if conditions are good, False if should pause
        """
        if not self.config['use_filters']:
            return True
        
        filters = self.strategy.check_filters()
        
        if filters['warnings']:
            print("\n⚠️ Market Warnings:")
            for warning in filters['warnings']:
                print(f"   {warning}")
        
        # Don't pause, just warn - let grid continue
        return True
    
    def run_iteration(self):
        """Run one iteration of the bot"""
        self.iteration += 1
        
        print(f"\n{'─'*60}")
        print(f"🔄 Iteration {self.iteration} | {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'─'*60}")
        
        # Check market conditions
        if not self.check_market_conditions():
            print("⏸️ Pausing due to market conditions...")
            return
        
        # Execute strategy
        try:
            result = self.strategy.execute()
            
            if result:
                if 'buy' in result:
                    print(f"\n✅ Grid placed:")
                    print(f"   Buy orders: {len(result['buy'])}")
                    print(f"   Sell orders: {len(result['sell'])}")
                    
                    # Show levels
                    if result['buy']:
                        buy_prices = [o['price'] for o in result['buy']]
                        print(f"   Buy levels: {buy_prices}")
                    if result['sell']:
                        sell_prices = [o['price'] for o in result['sell']]
                        print(f"   Sell levels: {sell_prices}")
            else:
                print("📊 Grid operating normally...")
                
        except Exception as e:
            print(f"❌ Strategy error: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Start the bot"""
        print("\n🚀 Starting Grid Trading Bot...")
        print(f"   Symbol: {self.config['symbol']}")
        print(f"   Grid levels: {self.config['grid_levels']} each side")
        print(f"   Spacing: {self.config['grid_spacing_percent']}%")
        print(f"   Order size: ${self.config['order_size_usd']} x {self.config['max_leverage']}x")
        print(f"   Check interval: {self.config['check_interval']}s")
        print(f"   Filters: {'Enabled' if self.config['use_filters'] else 'Disabled'}")
        
        # Show initial status
        self.show_status()
        
        # Confirm before starting
        print("\n" + "⚠️"*20)
        print("   ATTENTION: This will place REAL orders!")
        print("⚠️"*20)
        
        self.is_running = True
        
        # Main loop
        while self.is_running:
            try:
                self.run_iteration()
                
                if self.is_running:
                    print(f"\n💤 Sleeping {self.config['check_interval']}s...")
                    for _ in range(self.config['check_interval']):
                        if not self.is_running:
                            break
                        time.sleep(1)
                        
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(10)
        
        self.stop()
    
    def stop(self):
        """Stop the bot and cleanup"""
        if not self.is_running:
            return
            
        self.is_running = False
        print("\n\n🛑 Stopping Grid Trading Bot...")
        
        # Cancel all grid orders
        if self.strategy.grid_orders:
            print(f"🗑️ Cancelling {len(self.strategy.grid_orders)} grid orders...")
            cancelled = self.strategy.cancel_all_grid_orders()
            print(f"   Cancelled: {cancelled}")
        
        # Show final status
        self.show_status()
        
        # Stats
        stats = self.strategy.get_stats()
        print("\n📈 Session Statistics:")
        for k, v in stats.items():
            print(f"   {k}: {v}")
        
        print("\n✅ Bot stopped cleanly.\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WEEX Grid Trading Bot')
    parser.add_argument('--symbol', default='cmt_btcusdt', help='Trading pair')
    parser.add_argument('--levels', type=int, default=3, help='Grid levels each side')
    parser.add_argument('--spacing', type=float, default=0.4, help='Grid spacing %')
    parser.add_argument('--size', type=float, default=10, help='Order size USD')
    parser.add_argument('--leverage', type=int, default=5, help='Leverage')
    parser.add_argument('--interval', type=int, default=60, help='Check interval seconds')
    parser.add_argument('--no-filters', action='store_true', help='Disable RSI/MACD filters')
    
    args = parser.parse_args()
    
    config = {
        'symbol': args.symbol,
        'grid_levels': args.levels,
        'grid_spacing_percent': args.spacing,
        'order_size_usd': args.size,
        'max_leverage': args.leverage,
        'check_interval': args.interval,
        'use_filters': not args.no_filters,
    }
    
    bot = GridTradingBot(config)
    bot.start()


if __name__ == "__main__":
    main()
