"""Quick test for indicators"""
import sys
sys.path.insert(0, 'c:/Users/yamil/Desktop/sss')

from weex_client import WeexClient
from utils.indicators import TechnicalIndicators

print("Testing Technical Indicators...")
client = WeexClient()
ind = TechnicalIndicators(client, 'cmt_btcusdt')

# Get combined signal
result = ind.get_combined_signal()

print(f"\nPrice: ${result['price']:,.2f}")
print(f"Trend: {result['trend']}")
print(f"RSI: {result['rsi'].message}")
print(f"MACD: {result['macd'].message}")
print(f"Signal: {result['signal'].upper()} ({result['confidence']}%)")
