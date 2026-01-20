#!/usr/bin/env python3
"""
🧠 SMART AI SCALPER - HACKATHON WEEX 2026
Estrategia inteligente que combina TODAS las fuentes de datos

Combina:
1. CoinGecko Market Intelligence (trending, volume spikes, fear/greed)
2. DeepSeek AI Sentiment Analysis
3. RSI/MACD Technical Indicators
4. Whale Detection

Capital: $1,000 asignado
Meta: Maximizar ganancias con riesgo controlado

Características:
- AI-driven coin selection (no random)
- Multi-timeframe analysis
- Dynamic position sizing based on signal strength
- Trailing stops que se ajustan según volatilidad
- Kill switch si pierde demasiado
"""

import sys
import time
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

from weex_client import WeexClient
from utils.coingecko_intel import CoinGeckoIntel, MarketOpportunity
from utils.sentiment import DeepSeekSentiment

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN INTELIGENTE
# ═══════════════════════════════════════════════════════════════

# Capital Management (para $1,000)
INITIAL_CAPITAL = 1000           # Capital asignado
MAX_RISK_PER_TRADE = 0.02        # 2% máximo por trade ($20)
MAX_TOTAL_EXPOSURE = 0.50        # 50% del capital en posiciones ($500)
MAX_DAILY_LOSS = 0.10            # 10% max daily loss ($100)
MIN_BALANCE_TO_TRADE = 100       # Stop si balance < $100

# Position Sizing basado en confianza
LEVERAGE_BY_CONFIDENCE = {
    'high': 15,      # Confianza >80%: 15x
    'medium': 10,    # Confianza 60-80%: 10x
    'low': 5,        # Confianza <60%: 5x
}

# Risk/Reward
STOP_LOSS_PCT = 1.5              # 1.5% stop loss
TAKE_PROFIT_PCT = 4.0            # 4% take profit (2.67 R:R)
TRAILING_STOP_PCT = 1.0          # 1% trailing
TRAILING_ACTIVATION = 2.0        # Activar trailing después de +2%

# Timing
SCAN_INTERVAL = 20               # Escanear cada 20 segundos
POSITION_CHECK_INTERVAL = 5      # Verificar posiciones cada 5 segundos
COINGECKO_REFRESH = 120          # Actualizar CoinGecko cada 2 minutos
SENTIMENT_REFRESH = 300          # Actualizar sentiment cada 5 minutos

# Filters
MIN_SIGNAL_STRENGTH = 65         # Mínimo 65/100 para entrar
MAX_POSITIONS = 5                # Máximo 5 posiciones simultáneas
COOLDOWN_MINUTES = 3             # Cooldown entre trades misma coin

# Step sizes por moneda
STEP_SIZES = {
    'cmt_btcusdt': 0.001,
    'cmt_ethusdt': 0.01,
    'cmt_solusdt': 0.1,
    'cmt_bnbusdt': 0.1,
    'cmt_adausdt': 10,
    'cmt_dogeusdt': 100,
    'cmt_ltcusdt': 0.1,
    'cmt_xrpusdt': 10,
    'cmt_avaxusdt': 0.1,
    'cmt_dotusdt': 0.1,
    'cmt_linkusdt': 0.1,
    'cmt_nearusdt': 1,
    'cmt_uniusdt': 0.1,
    'cmt_arbusdt': 1,
    'cmt_suiusdt': 1,
    'cmt_aptusdt': 0.1,
    'cmt_pepeusdt': 1000000,
    'cmt_shibusdt': 100000,
}


@dataclass
class TradeSignal:
    """Señal de trading consolidada"""
    symbol: str
    direction: str  # 'long' or 'short'
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    size_usd: float
    leverage: int
    reasons: List[str]
    source: str  # 'coingecko', 'technical', 'sentiment', 'combined'


class SmartScalper:
    """
    AI-Powered Smart Scalper
    
    Combina múltiples fuentes de inteligencia para tomar
    decisiones de trading informadas.
    """
    
    def __init__(self):
        print("="*60)
        print("🧠 SMART AI SCALPER - WEEX HACKATHON")
        print("="*60)
        
        # Clients
        self.weex = WeexClient()
        self.coingecko = CoinGeckoIntel()
        self.sentiment = DeepSeekSentiment()
        
        # State
        self.positions = {}
        self.cooldowns = {}
        self.trailing_data = {}
        self.daily_pnl = 0
        self.total_pnl = 0
        self.trades_today = 0
        self.wins = 0
        self.losses = 0
        
        # Cache
        self.market_opportunities = []
        self.last_coingecko_update = 0
        self.last_sentiment_cache = {}
        self.fear_greed = {'value': 50, 'signal': 'neutral'}
        
        # Initialize
        self._update_balance()
        self._print_status()
    
    def _update_balance(self):
        """Update balance from WEEX"""
        try:
            assets = self.weex.get_account_assets()
            if isinstance(assets, list):
                for a in assets:
                    if a.get('coinName') == 'USDT':
                        self.equity = float(a.get('equity', 0))
                        self.available = float(a.get('available', 0))
                        self.frozen = float(a.get('frozen', 0))
                        self.unrealized_pnl = float(a.get('unrealizePnl', 0))
                        return True
        except Exception as e:
            print(f"❌ Error getting balance: {e}")
        
        self.equity = 0
        self.available = 0
        return False
    
    def _print_status(self):
        """Print current status"""
        print(f"\n💰 BALANCE:")
        print(f"   Equity: ${self.equity:.2f}")
        print(f"   Available: ${self.available:.2f}")
        print(f"   Unrealized P&L: ${self.unrealized_pnl:+.2f}")
        print(f"   Daily P&L: ${self.daily_pnl:+.2f}")
        print(f"   Trades Today: {self.trades_today}")
        if self.trades_today > 0:
            winrate = self.wins / self.trades_today * 100
            print(f"   Win Rate: {winrate:.1f}%")
    
    # ═══════════════════════════════════════════════════════════════
    # TECHNICAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, closes: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD, Signal, and Histogram"""
        if len(closes) < 26:
            return 0, 0, 0
        
        # EMA calculation
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_val = sum(data[:period]) / period
            for price in data[period:]:
                ema_val = (price - ema_val) * multiplier + ema_val
            return ema_val
        
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        macd_line = ema12 - ema26
        
        # Simple signal approximation
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_volatility(self, closes: List[float], period: int = 14) -> float:
        """Calculate volatility (ATR-like)"""
        if len(closes) < period:
            return 0.01
        
        changes = [abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        return sum(changes[-period:]) / period * 100  # As percentage
    
    def analyze_technical(self, symbol: str) -> Dict:
        """Full technical analysis for a symbol"""
        try:
            # Get candles
            candles = self.weex.get_candles(symbol, granularity='5m', limit=50)
            if not candles or len(candles) < 20:
                return None
            
            # Sort by timestamp
            candles_sorted = sorted(candles, key=lambda x: int(x[0]))
            
            closes = [float(c[4]) for c in candles_sorted]
            highs = [float(c[2]) for c in candles_sorted]
            lows = [float(c[3]) for c in candles_sorted]
            volumes = [float(c[5]) for c in candles_sorted]
            
            current_price = closes[-1]
            
            # Calculate indicators
            rsi = self.calculate_rsi(closes)
            macd, signal, histogram = self.calculate_macd(closes)
            volatility = self.calculate_volatility(closes)
            
            # Volume analysis
            avg_volume = sum(volumes[-10:]) / 10
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Price momentum (% change last 5 candles)
            momentum = (closes[-1] - closes[-5]) / closes[-5] * 100 if len(closes) >= 5 else 0
            
            # Determine signal
            signal_strength = 0
            direction = 'neutral'
            reasons = []
            
            # RSI signals
            if rsi < 30:
                signal_strength += 30
                direction = 'long'
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                signal_strength += 30
                direction = 'short'
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi < 40:
                signal_strength += 15
                direction = 'long'
                reasons.append(f"RSI low ({rsi:.1f})")
            elif rsi > 60:
                signal_strength += 15
                direction = 'short'
                reasons.append(f"RSI high ({rsi:.1f})")
            
            # MACD signals
            if histogram > 0 and direction in ['long', 'neutral']:
                signal_strength += 15
                direction = 'long'
                reasons.append("MACD bullish")
            elif histogram < 0 and direction in ['short', 'neutral']:
                signal_strength += 15
                direction = 'short'
                reasons.append("MACD bearish")
            
            # Volume confirmation
            if volume_ratio > 1.5:
                signal_strength += 10
                reasons.append(f"High volume ({volume_ratio:.1f}x)")
            
            # Momentum confirmation
            if momentum > 2 and direction == 'long':
                signal_strength += 10
                reasons.append(f"Strong momentum (+{momentum:.1f}%)")
            elif momentum < -2 and direction == 'short':
                signal_strength += 10
                reasons.append(f"Strong momentum ({momentum:.1f}%)")
            
            return {
                'symbol': symbol,
                'price': current_price,
                'rsi': rsi,
                'macd': macd,
                'histogram': histogram,
                'volatility': volatility,
                'volume_ratio': volume_ratio,
                'momentum': momentum,
                'direction': direction,
                'signal_strength': signal_strength,
                'reasons': reasons
            }
            
        except Exception as e:
            print(f"❌ Technical analysis error for {symbol}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # MARKET INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════
    
    def update_market_intel(self):
        """Update market intelligence from CoinGecko"""
        now = time.time()
        
        if now - self.last_coingecko_update < COINGECKO_REFRESH:
            return
        
        print("\n🦎 Updating CoinGecko intelligence...")
        
        # Get Fear & Greed
        self.fear_greed = self.coingecko.get_fear_greed_index()
        print(f"   Fear & Greed: {self.fear_greed['value']} ({self.fear_greed['classification']})")
        
        # Get opportunities
        self.market_opportunities = self.coingecko.find_opportunities()
        print(f"   Found {len(self.market_opportunities)} opportunities")
        
        self.last_coingecko_update = now
    
    def get_sentiment_signal(self, coin: str) -> Dict:
        """Get AI sentiment for a coin"""
        if not self.sentiment.enabled:
            return {'sentiment': 'neutral', 'confidence': 50}
        
        # Check cache
        cache_key = coin.upper()
        if cache_key in self.last_sentiment_cache:
            cached, timestamp = self.last_sentiment_cache[cache_key]
            if time.time() - timestamp < SENTIMENT_REFRESH:
                return cached
        
        try:
            result = self.sentiment.get_signal(coin)
            self.last_sentiment_cache[cache_key] = (result, time.time())
            return result
        except:
            return {'sentiment': 'neutral', 'confidence': 50}
    
    # ═══════════════════════════════════════════════════════════════
    # SIGNAL GENERATION
    # ═══════════════════════════════════════════════════════════════
    
    def generate_signals(self) -> List[TradeSignal]:
        """Generate trading signals from all sources"""
        signals = []
        
        # Update market intelligence
        self.update_market_intel()
        
        # Get tradeable coins from CoinGecko opportunities
        tradeable = set()
        for opp in self.market_opportunities[:10]:
            if opp.coin_id in self.coingecko.WEEX_MAPPING:
                tradeable.add(self.coingecko.WEEX_MAPPING[opp.coin_id])
        
        # Add default coins if not enough
        default_coins = ['cmt_btcusdt', 'cmt_ethusdt', 'cmt_solusdt', 'cmt_dogeusdt', 'cmt_adausdt']
        for coin in default_coins:
            tradeable.add(coin)
        
        print(f"\n🔍 Analyzing {len(tradeable)} coins...")
        
        for symbol in tradeable:
            # Skip if in cooldown
            if self.is_on_cooldown(symbol):
                continue
            
            # Skip if already have position
            if symbol in self.positions:
                continue
            
            # Technical analysis
            tech = self.analyze_technical(symbol)
            if not tech:
                continue
            
            # Get coin name for sentiment
            coin_name = symbol.replace('cmt_', '').replace('usdt', '').upper()
            
            # Combine signals
            total_strength = tech['signal_strength']
            all_reasons = tech['reasons'].copy()
            direction = tech['direction']
            
            # CoinGecko signal boost
            for opp in self.market_opportunities:
                if self.coingecko.WEEX_MAPPING.get(opp.coin_id) == symbol:
                    # Adjust direction based on signal type
                    if opp.signal_type == 'trending':
                        total_strength += 15
                        all_reasons.append(f"🔥 Trending coin")
                        if direction == 'neutral':
                            direction = 'long'
                    elif opp.signal_type == 'reversal':
                        total_strength += 20
                        if opp.change_24h > 10:  # Big gainer - potential short
                            if direction in ['short', 'neutral']:
                                direction = 'short'
                                all_reasons.append(f"📉 Reversal: +{opp.change_24h:.1f}% (SHORT)")
                        else:  # Big loser - potential long
                            if direction in ['long', 'neutral']:
                                direction = 'long'
                                all_reasons.append(f"📈 Bounce: {opp.change_24h:.1f}% (LONG)")
                    elif opp.signal_type == 'volume_spike':
                        total_strength += 10
                        all_reasons.append(f"🐋 Whale activity detected")
                    break
            
            # Fear & Greed adjustment
            if self.fear_greed['value'] < 25:  # Extreme fear
                if direction == 'long':
                    total_strength += 10
                    all_reasons.append("😱 Extreme fear (contrarian buy)")
            elif self.fear_greed['value'] > 75:  # Extreme greed
                if direction == 'short':
                    total_strength += 10
                    all_reasons.append("🤑 Extreme greed (contrarian sell)")
            
            # Sentiment analysis (only for strong technical signals)
            if total_strength >= 50 and self.sentiment.enabled:
                sent = self.get_sentiment_signal(coin_name)
                if sent['sentiment'] == 'bullish' and direction == 'long':
                    total_strength += 15
                    all_reasons.append(f"🤖 AI bullish ({sent['confidence']:.0f}%)")
                elif sent['sentiment'] == 'bearish' and direction == 'short':
                    total_strength += 15
                    all_reasons.append(f"🤖 AI bearish ({sent['confidence']:.0f}%)")
            
            # Skip if not strong enough
            if total_strength < MIN_SIGNAL_STRENGTH or direction == 'neutral':
                continue
            
            # Calculate position parameters
            confidence = min(100, total_strength)
            
            # Determine leverage based on confidence
            if confidence >= 80:
                leverage = LEVERAGE_BY_CONFIDENCE['high']
            elif confidence >= 60:
                leverage = LEVERAGE_BY_CONFIDENCE['medium']
            else:
                leverage = LEVERAGE_BY_CONFIDENCE['low']
            
            # Calculate position size
            risk_amount = self.available * MAX_RISK_PER_TRADE
            size_usd = min(risk_amount * leverage, self.available * 0.2)  # Max 20% of available per trade
            
            # Calculate stops
            price = tech['price']
            volatility = max(tech['volatility'], 0.5)  # Min 0.5% volatility
            
            # Adjust stops based on volatility
            sl_pct = STOP_LOSS_PCT * (1 + volatility * 0.1)
            tp_pct = TAKE_PROFIT_PCT * (1 + volatility * 0.1)
            
            if direction == 'long':
                stop_loss = price * (1 - sl_pct / 100)
                take_profit = price * (1 + tp_pct / 100)
            else:
                stop_loss = price * (1 + sl_pct / 100)
                take_profit = price * (1 - tp_pct / 100)
            
            signals.append(TradeSignal(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                size_usd=size_usd,
                leverage=leverage,
                reasons=all_reasons,
                source='combined'
            ))
        
        # Sort by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        return signals
    
    # ═══════════════════════════════════════════════════════════════
    # POSITION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def get_step_size(self, symbol: str) -> float:
        """Get step size for symbol"""
        return STEP_SIZES.get(symbol, 0.01)
    
    def calculate_quantity(self, symbol: str, price: float, size_usd: float, leverage: int) -> float:
        """Calculate order quantity"""
        notional = size_usd * leverage
        raw_qty = notional / price
        step = self.get_step_size(symbol)
        qty = round(raw_qty / step) * step
        
        # Ensure proper decimals
        decimals = len(str(step).split('.')[-1]) if '.' in str(step) else 0
        return round(qty, decimals)
    
    def is_on_cooldown(self, symbol: str) -> bool:
        """Check if symbol is on cooldown"""
        if symbol not in self.cooldowns:
            return False
        elapsed = (datetime.now() - self.cooldowns[symbol]).total_seconds()
        return elapsed < COOLDOWN_MINUTES * 60
    
    def set_cooldown(self, symbol: str):
        """Set cooldown for symbol"""
        self.cooldowns[symbol] = datetime.now()
    
    def open_position(self, signal: TradeSignal) -> bool:
        """Open a new position based on signal"""
        try:
            # Safety checks
            if len(self.positions) >= MAX_POSITIONS:
                print(f"⚠️ Max positions reached ({MAX_POSITIONS})")
                return False
            
            if self.available < 50:
                print("⚠️ Low balance, skipping trade")
                return False
            
            if abs(self.daily_pnl) > self.equity * MAX_DAILY_LOSS:
                print("🛑 Daily loss limit reached, stopping")
                return False
            
            # Set leverage
            print(f"\n🎯 Opening {signal.direction.upper()} on {signal.symbol}")
            print(f"   Confidence: {signal.confidence:.0f}%")
            print(f"   Reasons: {', '.join(signal.reasons)}")
            
            self.weex.set_leverage(signal.symbol, signal.leverage)
            
            # Calculate quantity
            qty = self.calculate_quantity(
                signal.symbol, 
                signal.entry_price, 
                signal.size_usd, 
                signal.leverage
            )
            
            if qty <= 0:
                print("❌ Invalid quantity")
                return False
            
            # Place order
            side = 'buy' if signal.direction == 'long' else 'sell'
            
            result = self.weex.place_order(
                symbol=signal.symbol,
                side=side,
                size=qty,
                order_type='market'
            )
            
            if result and result.get('orderId'):
                print(f"✅ Order placed: {result['orderId']}")
                
                # Track position
                self.positions[signal.symbol] = {
                    'order_id': result['orderId'],
                    'direction': signal.direction,
                    'entry_price': signal.entry_price,
                    'quantity': qty,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'leverage': signal.leverage,
                    'size_usd': signal.size_usd,
                    'highest_price': signal.entry_price,
                    'lowest_price': signal.entry_price,
                    'trailing_active': False,
                    'open_time': datetime.now(),
                    'reasons': signal.reasons
                }
                
                self.set_cooldown(signal.symbol)
                self.trades_today += 1
                
                return True
            else:
                print(f"❌ Order failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error opening position: {e}")
            return False
    
    def check_positions(self):
        """Check and manage open positions"""
        if not self.positions:
            return
        
        for symbol, pos in list(self.positions.items()):
            try:
                # Get current price
                ticker = self.weex.get_ticker(symbol)
                if not ticker:
                    continue
                
                ticker_data = ticker.get('data', ticker) if isinstance(ticker, dict) else ticker
                current_price = float(ticker_data.get('last', 0))
                
                if current_price <= 0:
                    continue
                
                entry = pos['entry_price']
                direction = pos['direction']
                
                # Calculate P&L %
                if direction == 'long':
                    pnl_pct = (current_price - entry) / entry * 100
                    pos['highest_price'] = max(pos['highest_price'], current_price)
                else:
                    pnl_pct = (entry - current_price) / entry * 100
                    pos['lowest_price'] = min(pos['lowest_price'], current_price)
                
                pnl_usd = pnl_pct * pos['size_usd'] * pos['leverage'] / 100
                
                should_close = False
                reason = ""
                
                # Check stop loss
                if direction == 'long' and current_price <= pos['stop_loss']:
                    should_close = True
                    reason = "Stop Loss"
                elif direction == 'short' and current_price >= pos['stop_loss']:
                    should_close = True
                    reason = "Stop Loss"
                
                # Check take profit
                if direction == 'long' and current_price >= pos['take_profit']:
                    should_close = True
                    reason = "Take Profit"
                elif direction == 'short' and current_price <= pos['take_profit']:
                    should_close = True
                    reason = "Take Profit"
                
                # Trailing stop logic
                if pnl_pct >= TRAILING_ACTIVATION:
                    pos['trailing_active'] = True
                
                if pos['trailing_active']:
                    if direction == 'long':
                        trailing_stop = pos['highest_price'] * (1 - TRAILING_STOP_PCT / 100)
                        if current_price <= trailing_stop:
                            should_close = True
                            reason = "Trailing Stop"
                    else:
                        trailing_stop = pos['lowest_price'] * (1 + TRAILING_STOP_PCT / 100)
                        if current_price >= trailing_stop:
                            should_close = True
                            reason = "Trailing Stop"
                
                # Close if needed
                if should_close:
                    self.close_position(symbol, reason, pnl_usd)
                else:
                    # Print update every 30 seconds
                    elapsed = (datetime.now() - pos['open_time']).total_seconds()
                    if elapsed % 30 < POSITION_CHECK_INTERVAL:
                        trailing_str = "🎯" if pos['trailing_active'] else ""
                        print(f"   {symbol}: {pnl_pct:+.2f}% (${pnl_usd:+.2f}) {trailing_str}")
                
            except Exception as e:
                print(f"❌ Error checking {symbol}: {e}")
    
    def close_position(self, symbol: str, reason: str, pnl_usd: float):
        """Close a position"""
        try:
            pos = self.positions.get(symbol)
            if not pos:
                return
            
            # Close by placing opposite order
            side = 'sell' if pos['direction'] == 'long' else 'buy'
            
            result = self.weex.place_order(
                symbol=symbol,
                side=side,
                size=pos['quantity'],
                order_type='market'
            )
            
            if result:
                # Update stats
                self.daily_pnl += pnl_usd
                self.total_pnl += pnl_usd
                
                if pnl_usd > 0:
                    self.wins += 1
                    emoji = "💰"
                else:
                    self.losses += 1
                    emoji = "❌"
                
                print(f"\n{emoji} CLOSED {symbol} - {reason}")
                print(f"   P&L: ${pnl_usd:+.2f}")
                print(f"   Daily P&L: ${self.daily_pnl:+.2f}")
                
                # Remove from tracking
                del self.positions[symbol]
                
        except Exception as e:
            print(f"❌ Error closing {symbol}: {e}")
    
    def close_all_positions(self):
        """Emergency close all positions"""
        print("\n🛑 Closing all positions...")
        for symbol in list(self.positions.keys()):
            self.close_position(symbol, "Manual Close", 0)
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════
    
    def run(self):
        """Main trading loop"""
        print("\n🚀 Starting Smart AI Scalper...")
        print(f"   Capital: ${self.equity:.2f}")
        print(f"   Max Risk/Trade: {MAX_RISK_PER_TRADE*100}%")
        print(f"   Max Positions: {MAX_POSITIONS}")
        print(f"   Min Signal Strength: {MIN_SIGNAL_STRENGTH}")
        
        last_scan = 0
        
        try:
            while True:
                now = time.time()
                
                # Update balance
                self._update_balance()
                
                # Safety checks
                if self.equity < MIN_BALANCE_TO_TRADE:
                    print(f"\n🛑 Balance too low (${self.equity:.2f}). Stopping.")
                    break
                
                if abs(self.daily_pnl) > self.equity * MAX_DAILY_LOSS:
                    print(f"\n🛑 Daily loss limit reached (${self.daily_pnl:.2f}). Stopping.")
                    break
                
                # Check existing positions
                self.check_positions()
                
                # Generate new signals (every SCAN_INTERVAL seconds)
                if now - last_scan >= SCAN_INTERVAL:
                    signals = self.generate_signals()
                    
                    if signals:
                        print(f"\n📊 Top signals:")
                        for s in signals[:3]:
                            print(f"   {s.symbol}: {s.direction.upper()} "
                                  f"({s.confidence:.0f}%) - {', '.join(s.reasons[:2])}")
                        
                        # Try to open position on best signal
                        for signal in signals[:2]:  # Top 2 signals
                            if len(self.positions) < MAX_POSITIONS:
                                if self.open_position(signal):
                                    break
                    
                    last_scan = now
                
                # Status update
                if int(now) % 60 == 0:
                    self._print_status()
                
                time.sleep(POSITION_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
            self.close_all_positions()
        
        print("\n" + "="*60)
        print("📊 FINAL STATS:")
        print(f"   Total P&L: ${self.total_pnl:+.2f}")
        print(f"   Total Trades: {self.trades_today}")
        if self.trades_today > 0:
            print(f"   Win Rate: {self.wins/self.trades_today*100:.1f}%")
        print("="*60)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    bot = SmartScalper()
    bot.run()
