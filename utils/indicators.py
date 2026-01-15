"""
📊 Technical Indicators Module
RSI, MACD, and other indicators for trading signals
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class IndicatorSignal:
    """Standardized indicator signal"""
    name: str
    value: float
    signal: str  # 'buy', 'sell', 'neutral'
    strength: float  # 0-100
    message: str


class TechnicalIndicators:
    """
    Technical Analysis Indicators
    
    Calculates RSI, MACD, and other indicators from price data
    """
    
    def __init__(self, client, symbol: str = "cmt_btcusdt"):
        """
        Initialize with WEEX client
        
        Args:
            client: WeexClient instance
            symbol: Trading pair
        """
        self.client = client
        self.symbol = symbol
        self.price_history: List[float] = []
        self.max_history = 100  # Keep last 100 candles
    
    def fetch_candles(self, granularity: str = "1m", limit: int = 50) -> List[Dict]:
        """
        Fetch candlestick data from WEEX
        
        Args:
            granularity: Candle interval (1m, 5m, 15m, 1h, etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of candle dicts with open, high, low, close, volume
        """
        import requests
        
        try:
            # WEEX candle endpoint
            url = f"{self.client.BASE_URL}/capi/v2/market/candles"
            params = {
                "symbol": self.symbol,
                "granularity": granularity,
                "limit": str(limit)
            }
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                candles = []
                for candle in data:
                    # Format: [timestamp, open, high, low, close, volume]
                    if isinstance(candle, list) and len(candle) >= 6:
                        candles.append({
                            'timestamp': candle[0],
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[5])
                        })
                
                # Update price history
                self.price_history = [c['close'] for c in candles]
                return candles
            
            return []
            
        except Exception as e:
            print(f"❌ Failed to fetch candles: {e}")
            return []
    
    def calculate_rsi(self, prices: List[float] = None, period: int = 14) -> IndicatorSignal:
        """
        Calculate Relative Strength Index (RSI)
        
        RSI measures momentum:
        - RSI > 70: Overbought (potential sell)
        - RSI < 30: Oversold (potential buy)
        - RSI 40-60: Neutral
        
        Args:
            prices: Price list (uses internal history if None)
            period: RSI period (default 14)
            
        Returns:
            IndicatorSignal with RSI value and signal
        """
        prices = prices or self.price_history
        
        if len(prices) < period + 1:
            return IndicatorSignal(
                name="RSI",
                value=50.0,
                signal="neutral",
                strength=0,
                message=f"Insufficient data ({len(prices)} < {period + 1})"
            )
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Calculate average gain/loss over period
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        # Calculate RS and RSI
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Determine signal
        if rsi >= 70:
            signal = "sell"
            strength = min((rsi - 70) * 3.33, 100)  # 70-100 maps to 0-100
            message = f"🔴 Overbought ({rsi:.1f})"
        elif rsi <= 30:
            signal = "buy"
            strength = min((30 - rsi) * 3.33, 100)  # 0-30 maps to 100-0
            message = f"🟢 Oversold ({rsi:.1f})"
        else:
            signal = "neutral"
            strength = 50 - abs(50 - rsi)  # Strongest at 50
            message = f"⚪ Neutral ({rsi:.1f})"
        
        return IndicatorSignal(
            name="RSI",
            value=round(rsi, 2),
            signal=signal,
            strength=round(strength, 1),
            message=message
        )
    
    def calculate_macd(self, prices: List[float] = None, 
                       fast: int = 12, slow: int = 26, 
                       signal_period: int = 9) -> IndicatorSignal:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        MACD measures trend:
        - MACD > Signal line: Bullish
        - MACD < Signal line: Bearish
        - Histogram increasing: Momentum building
        
        Args:
            prices: Price list
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
            
        Returns:
            IndicatorSignal with MACD value and signal
        """
        prices = prices or self.price_history
        
        if len(prices) < slow + signal_period:
            return IndicatorSignal(
                name="MACD",
                value=0.0,
                signal="neutral",
                strength=0,
                message=f"Insufficient data ({len(prices)} < {slow + signal_period})"
            )
        
        def ema(data: List[float], period: int) -> List[float]:
            """Calculate EMA"""
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]  # SMA for first value
            
            for price in data[period:]:
                ema_values.append((price * multiplier) + (ema_values[-1] * (1 - multiplier)))
            
            return ema_values
        
        # Calculate EMAs
        ema_fast = ema(prices, fast)
        ema_slow = ema(prices, slow)
        
        # MACD line = Fast EMA - Slow EMA
        # Align arrays (slow EMA starts later)
        offset = slow - fast
        macd_line = [ema_fast[i + offset] - ema_slow[i] for i in range(len(ema_slow))]
        
        # Signal line = EMA of MACD line
        if len(macd_line) >= signal_period:
            signal_line = ema(macd_line, signal_period)
        else:
            signal_line = [0]
        
        # Current values
        macd_current = macd_line[-1] if macd_line else 0
        signal_current = signal_line[-1] if signal_line else 0
        histogram = macd_current - signal_current
        
        # Previous histogram for momentum
        if len(macd_line) > 1 and len(signal_line) > 1:
            prev_histogram = macd_line[-2] - signal_line[-2]
            momentum_increasing = histogram > prev_histogram
        else:
            momentum_increasing = False
        
        # Determine signal
        if macd_current > signal_current:
            signal = "buy"
            strength = min(abs(histogram) * 100, 100)
            emoji = "📈" if momentum_increasing else "🟢"
            message = f"{emoji} Bullish (MACD: {macd_current:.2f})"
        elif macd_current < signal_current:
            signal = "sell"
            strength = min(abs(histogram) * 100, 100)
            emoji = "📉" if not momentum_increasing else "🔴"
            message = f"{emoji} Bearish (MACD: {macd_current:.2f})"
        else:
            signal = "neutral"
            strength = 0
            message = f"⚪ Neutral (MACD: {macd_current:.2f})"
        
        return IndicatorSignal(
            name="MACD",
            value=round(macd_current, 4),
            signal=signal,
            strength=round(strength, 1),
            message=message
        )
    
    def calculate_sma(self, prices: List[float] = None, period: int = 20) -> float:
        """Calculate Simple Moving Average"""
        prices = prices or self.price_history
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float] = None, period: int = 20) -> float:
        """Calculate Exponential Moving Average"""
        prices = prices or self.price_history
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def get_trend(self) -> str:
        """
        Determine overall trend using multiple MAs
        
        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        if len(self.price_history) < 50:
            return "unknown"
        
        current_price = self.price_history[-1]
        sma_20 = self.calculate_sma(period=20)
        sma_50 = self.calculate_sma(period=50)
        
        if current_price > sma_20 > sma_50:
            return "uptrend"
        elif current_price < sma_20 < sma_50:
            return "downtrend"
        else:
            return "sideways"
    
    def get_combined_signal(self) -> Dict:
        """
        Get combined signal from RSI and MACD
        
        Returns:
            Dict with overall signal and individual indicators
        """
        # Fetch fresh data
        self.fetch_candles(granularity="5m", limit=50)
        
        rsi = self.calculate_rsi()
        macd = self.calculate_macd()
        trend = self.get_trend()
        
        # Combine signals
        buy_score = 0
        sell_score = 0
        
        if rsi.signal == "buy":
            buy_score += rsi.strength
        elif rsi.signal == "sell":
            sell_score += rsi.strength
        
        if macd.signal == "buy":
            buy_score += macd.strength
        elif macd.signal == "sell":
            sell_score += macd.strength
        
        # Trend bonus
        if trend == "uptrend":
            buy_score += 20
        elif trend == "downtrend":
            sell_score += 20
        
        # Determine overall signal
        if buy_score > sell_score + 30:  # Need significant difference
            overall = "buy"
            confidence = min(buy_score / 2, 100)
        elif sell_score > buy_score + 30:
            overall = "sell"
            confidence = min(sell_score / 2, 100)
        else:
            overall = "neutral"
            confidence = 50
        
        return {
            'signal': overall,
            'confidence': round(confidence, 1),
            'trend': trend,
            'rsi': rsi,
            'macd': macd,
            'price': self.price_history[-1] if self.price_history else 0
        }


# Quick test
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    from weex_client import WeexClient
    
    print("\n📊 Testing Technical Indicators")
    print("="*50)
    
    client = WeexClient()
    indicators = TechnicalIndicators(client, "cmt_btcusdt")
    
    # Get combined signal
    result = indicators.get_combined_signal()
    
    print(f"\n📈 Current Price: ${result['price']:,.2f}")
    print(f"📊 Trend: {result['trend']}")
    print(f"\n🔍 RSI: {result['rsi'].message}")
    print(f"🔍 MACD: {result['macd'].message}")
    print(f"\n🎯 Overall Signal: {result['signal'].upper()}")
    print(f"💪 Confidence: {result['confidence']}%")
