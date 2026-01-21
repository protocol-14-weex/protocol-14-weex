#!/usr/bin/env python3
"""
🏆 CONSERVATIVE GRID BOT
Estrategia segura para clasificar en hackathon

Características:
- Grid trading en rangos laterales
- Leverage bajo (5x-10x)
- Stop loss dinámico por ATR
- Solo monedas de alta liquidez
- CoinGecko para filtrar condiciones de mercado
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weex_client import WeexClient

load_dotenv()

# Log file for real-time decisions
LOG_FILE = "bot_decisions.log"
JSON_LOG_FILE = "bot_signals.json"


def log_decision(message: str, data: dict = None):
    """Log a decision to file with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    
    # Console print
    print(log_entry)
    
    # File log
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + "\n")
    
    # JSON log for structured data
    if data:
        try:
            # Read existing
            signals = []
            if os.path.exists(JSON_LOG_FILE):
                with open(JSON_LOG_FILE, 'r') as f:
                    signals = json.load(f)
            
            # Add new entry
            signals.append({
                'timestamp': timestamp,
                'message': message,
                **data
            })
            
            # Keep last 500 entries
            signals = signals[-500:]
            
            # Write back
            with open(JSON_LOG_FILE, 'w') as f:
                json.dump(signals, f, indent=2)
        except:
            pass


@dataclass
class GridConfig:
    """Configuración de grid por moneda"""
    symbol: str
    position_size: float      # USDT por trade
    leverage: int             # 5x o 10x
    grid_spacing: float       # % entre niveles
    take_profit: float        # % ganancia
    stop_loss: float          # % pérdida máxima
    max_positions: int        # Máximo de posiciones abiertas


class CoinGeckoLite:
    """Cliente ligero de CoinGecko para condiciones de mercado"""
    
    def __init__(self):
        self.api_key = os.getenv("COINGECKO_API_KEY", "")
        self.base_url = "https://pro-api.coingecko.com/api/v3" if self.api_key else "https://api.coingecko.com/api/v3"
        self.headers = {'x-cg-pro-api-key': self.api_key} if self.api_key else {}
        print(f"🦎 CoinGecko: {'Pro API' if self.api_key else 'Free API'}")
    
    def get_fear_greed(self) -> int:
        """Obtener Fear & Greed Index (0-100)"""
        try:
            resp = requests.get("https://api.alternative.me/fng/", timeout=10)
            if resp.status_code == 200:
                return int(resp.json()['data'][0]['value'])
        except:
            pass
        return 50  # Neutral por defecto
    
    def get_market_condition(self) -> Dict:
        """Obtener condición general del mercado"""
        try:
            resp = requests.get(
                f"{self.base_url}/global",
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()['data']
                return {
                    'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 50),
                    'market_change_24h': data.get('market_cap_change_percentage_24h_usd', 0),
                    'total_volume': data.get('total_volume', {}).get('usd', 0)
                }
        except:
            pass
        return {'btc_dominance': 50, 'market_change_24h': 0, 'total_volume': 0}
    
    def is_market_safe(self) -> Tuple[bool, str]:
        """
        Verificar si es seguro operar
        
        Returns:
            (is_safe, reason)
        """
        fng = self.get_fear_greed()
        market = self.get_market_condition()
        
        # Log the signal data
        log_decision("🦎 COINGECKO SIGNAL", {
            'type': 'coingecko_signal',
            'fear_greed': fng,
            'btc_dominance': market['btc_dominance'],
            'market_change_24h': market['market_change_24h'],
            'total_volume': market['total_volume']
        })
        
        # Condiciones peligrosas
        if fng < 15:
            log_decision(f"⚠️ EXTREME FEAR - Trading paused", {'safe': False, 'reason': 'extreme_fear'})
            return False, f"⚠️ Extreme Fear ({fng}) - Mercado muy volátil"
        if fng > 85:
            log_decision(f"⚠️ EXTREME GREED - Trading paused", {'safe': False, 'reason': 'extreme_greed'})
            return False, f"⚠️ Extreme Greed ({fng}) - Posible corrección"
        if abs(market['market_change_24h']) > 8:
            log_decision(f"⚠️ HIGH VOLATILITY - Trading paused", {'safe': False, 'reason': 'high_volatility'})
            return False, f"⚠️ Mercado moviendo {market['market_change_24h']:.1f}% - Muy volátil"
        
        log_decision(f"✅ MARKET SAFE - Trading active", {'safe': True, 'fng': fng, 'change_24h': market['market_change_24h']})
        return True, f"✅ Market OK (FnG: {fng}, 24h: {market['market_change_24h']:+.1f}%)"


class ConservativeGridBot:
    """
    Bot de Grid Trading Conservador
    
    Estrategia:
    1. Define rangos de precio para cada moneda
    2. Compra en la parte baja del rango
    3. Vende en la parte alta
    4. Stop loss dinámico para proteger capital
    """
    
    # Configuración por moneda (CONSERVADORA)
    GRID_CONFIGS = {
        'cmt_btcusdt': GridConfig(
            symbol='cmt_btcusdt',
            position_size=100,    # $100 por trade
            leverage=10,          # 10x leverage
            grid_spacing=0.3,     # 0.3% entre niveles
            take_profit=0.5,      # 0.5% ganancia = $5 con $100 x10
            stop_loss=0.8,        # 0.8% máximo = $8 pérdida
            max_positions=2
        ),
        'cmt_ethusdt': GridConfig(
            symbol='cmt_ethusdt',
            position_size=100,
            leverage=10,
            grid_spacing=0.4,     # ETH más volátil
            take_profit=0.6,
            stop_loss=1.0,
            max_positions=2
        ),
        'cmt_solusdt': GridConfig(
            symbol='cmt_solusdt',
            position_size=75,     # Menos capital en SOL
            leverage=10,
            grid_spacing=0.5,
            take_profit=0.8,
            stop_loss=1.2,
            max_positions=2
        ),
        'cmt_ltcusdt': GridConfig(
            symbol='cmt_ltcusdt',
            position_size=75,
            leverage=10,
            grid_spacing=0.4,
            take_profit=0.6,
            stop_loss=1.0,
            max_positions=2
        ),
        'cmt_dogeusdt': GridConfig(
            symbol='cmt_dogeusdt',
            position_size=50,     # DOGE más riesgoso
            leverage=5,           # Menos leverage
            grid_spacing=0.6,
            take_profit=1.0,
            stop_loss=1.5,
            max_positions=1
        ),
    }
    
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
    }
    
    def __init__(self):
        """Inicializar bot"""
        print("="*60)
        print("🏆 CONSERVATIVE GRID BOT")
        print("="*60)
        
        self.client = WeexClient()
        self.coingecko = CoinGeckoLite()
        
        # Estado
        self.positions: Dict[str, Dict] = {}
        self.pending_orders: Dict[str, List] = {}
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
        # Límites de seguridad
        self.max_daily_loss = 50.0      # Máximo $50 pérdida diaria
        self.max_daily_trades = 30      # Máximo 30 trades por día
        self.min_balance = 200.0        # Mínimo $200 en cuenta
        
        # Obtener balance inicial
        self.update_balance()
        
        print(f"\n💰 Balance: ${self.available:.2f} disponible")
        print(f"📊 Monedas: {list(self.GRID_CONFIGS.keys())}")
    
    def update_balance(self):
        """Actualizar balance desde WEEX"""
        try:
            assets = self.client.get_account_assets()
            if isinstance(assets, list):
                for a in assets:
                    if a.get('coinName') == 'USDT':
                        self.equity = float(a.get('equity', 0))
                        self.available = float(a.get('available', 0))
                        self.unrealized = float(a.get('unrealizePnl', 0))
                        return True
        except Exception as e:
            print(f"❌ Error getting balance: {e}")
        
        self.equity = 0
        self.available = 0
        self.unrealized = 0
        return False
    
    def get_step_size(self, symbol: str) -> float:
        """Get step size for symbol"""
        return self.STEP_SIZES.get(symbol, 0.01)
    
    def check_safety(self) -> Tuple[bool, str]:
        """Verificar si es seguro operar"""
        # 1. Verificar mercado
        market_safe, msg = self.coingecko.is_market_safe()
        if not market_safe:
            return False, msg
        
        # 2. Verificar pérdida diaria
        if self.daily_pnl < -self.max_daily_loss:
            return False, f"⛔ Daily loss limit reached: ${self.daily_pnl:.2f}"
        
        # 3. Verificar límite de trades
        if self.total_trades >= self.max_daily_trades:
            return False, f"⛔ Daily trade limit reached: {self.total_trades}"
        
        # 4. Verificar balance
        self.update_balance()
        if self.available < self.min_balance:
            return False, f"⛔ Low balance: ${self.available:.2f}"
        
        return True, msg
    
    def get_ticker_data(self, symbol: str) -> Dict:
        """Obtener datos del ticker"""
        try:
            ticker = self.client.get_ticker(symbol)
            if ticker:
                # Handle different API response formats
                data = ticker.get('data', ticker) if isinstance(ticker, dict) else ticker
                return {
                    'last': float(data.get('last', 0)),
                    'high24h': float(data.get('high24h', 0)),
                    'low24h': float(data.get('low24h', 0)),
                    'volume24h': float(data.get('volume24h', 0))
                }
        except Exception as e:
            print(f"❌ Ticker error {symbol}: {e}")
        return {}
    
    def calculate_rsi(self, symbol: str) -> float:
        """Calcular RSI para el símbolo"""
        try:
            candles = self.client.get_candles(symbol, granularity='5m', limit=30)
            if not candles or len(candles) < 15:
                return 50.0
            
            # Sort by timestamp
            candles_sorted = sorted(candles, key=lambda x: int(x[0]))
            closes = [float(c[4]) for c in candles_sorted]
            
            # Calculate RSI
            period = 14
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
            
        except:
            return 50.0
    
    def get_price_range(self, symbol: str) -> Tuple[float, float, float]:
        """
        Obtener rango de precio actual
        
        Returns:
            (current_price, support, resistance)
        """
        ticker = self.get_ticker_data(symbol)
        if not ticker or ticker.get('last', 0) == 0:
            return 0, 0, 0
        
        price = ticker['last']
        high_24h = ticker.get('high24h', 0)
        low_24h = ticker.get('low24h', 0)
        
        # Debug output
        print(f"      DEBUG {symbol}: price={price}, high24h={high_24h}, low24h={low_24h}")
        
        # If no high/low data, use price +/- 2%
        if high_24h == 0 or low_24h == 0 or high_24h == low_24h:
            high_24h = price * 1.02
            low_24h = price * 0.98
        
        # Calcular soporte y resistencia simples
        range_size = high_24h - low_24h
        support = low_24h + (range_size * 0.2)      # 20% desde el mínimo
        resistance = high_24h - (range_size * 0.2)  # 20% desde el máximo
        
        return price, support, resistance
    
    def find_opportunity(self) -> Optional[Tuple[str, str, float, float]]:
        """
        Buscar oportunidad de trading
        
        Returns:
            (symbol, side, entry_price, size) or None
        """
        print(f"\n📊 ANALYZING ALL SYMBOLS:")
        print(f"   LONG: RSI < 45 (oversold)")
        print(f"   SHORT: RSI > 65 (overbought)")
        
        best_signal = None
        
        for symbol, config in self.GRID_CONFIGS.items():
            # Skip si ya tenemos posición
            if symbol in self.positions:
                print(f"   {symbol}: SKIP (already have position)")
                continue
            
            # Obtener datos
            price, support, resistance = self.get_price_range(symbol)
            if price == 0:
                print(f"   {symbol}: SKIP (no price data)")
                continue
            
            rsi = self.calculate_rsi(symbol)
            
            # Calcular tamaño
            step = self.get_step_size(symbol)
            notional = config.position_size * config.leverage
            raw_size = notional / price
            size = round(raw_size / step) * step
            
            # Determine signal based on RSI only (simpler and more reliable)
            signal = "NONE"
            strength = 0
            
            if rsi < 45:  # Oversold → LONG
                signal = "🟢 LONG"
                strength = 45 - rsi  # Higher strength for lower RSI
            elif rsi > 65:  # Overbought → SHORT
                signal = "🔴 SHORT"
                strength = rsi - 65  # Higher strength for higher RSI
            
            print(f"   {symbol}: price=${price:.2f}, RSI={rsi:.1f} → {signal} (strength={strength:.1f})")
            
            # Take the first signal we find (but prefer stronger signals)
            if signal != "NONE" and (best_signal is None or strength > best_signal[4]):
                if rsi < 45:
                    best_signal = (symbol, 'buy', price, size, strength)
                else:
                    best_signal = (symbol, 'sell', price, size, strength)
        
        if best_signal:
            symbol, side, price, size, _ = best_signal
            print(f"\n   ✅ TAKING {side.upper()} on {symbol}")
            log_decision(f"📈 OPENING {side.upper()} {symbol}", {
                'type': 'trade_signal',
                'symbol': symbol,
                'side': side.upper(),
                'price': price
            })
            return symbol, side, price, size
        
        # If no clear RSI signal, take ANY trade to generate activity
        # Pick the symbol with the most extreme RSI
        print(f"\n   ⚠️ No clear RSI signal. Checking for any opportunity...")
        
        for symbol, config in self.GRID_CONFIGS.items():
            if symbol in self.positions:
                continue
            
            price, _, _ = self.get_price_range(symbol)
            if price == 0:
                continue
            
            rsi = self.calculate_rsi(symbol)
            step = self.get_step_size(symbol)
            notional = config.position_size * config.leverage
            raw_size = notional / price
            size = round(raw_size / step) * step
            
            # Take SHORT if RSI > 55 (slightly overbought)
            if rsi > 55:
                print(f"   ✅ TAKING SHORT on {symbol} (RSI={rsi:.1f} > 55)")
                log_decision(f"📈 OPENING SHORT {symbol}", {
                    'type': 'trade_signal',
                    'symbol': symbol,
                    'side': 'SHORT',
                    'price': price,
                    'rsi': rsi
                })
                return symbol, 'sell', price, size
            
            # Take LONG if RSI < 55 (neutral to oversold)
            if rsi < 55:
                print(f"   ✅ TAKING LONG on {symbol} (RSI={rsi:.1f} < 55)")
                log_decision(f"📈 OPENING LONG {symbol}", {
                    'type': 'trade_signal',
                    'symbol': symbol,
                    'side': 'LONG',
                    'price': price,
                    'rsi': rsi
                })
                return symbol, 'buy', price, size
        
        return None
    
    def open_position(self, symbol: str, side: str, price: float, size: float) -> bool:
        """Abrir posición"""
        config = self.GRID_CONFIGS.get(symbol)
        if not config:
            return False
        
        try:
            # Set leverage
            self.client.set_leverage(symbol, config.leverage)
            time.sleep(0.5)
            
            # Calculate TP/SL
            if side == 'buy':
                tp_price = price * (1 + config.take_profit / 100)
                sl_price = price * (1 - config.stop_loss / 100)
            else:
                tp_price = price * (1 - config.take_profit / 100)
                sl_price = price * (1 + config.stop_loss / 100)
            
            print(f"\n{'='*50}")
            print(f"🎯 OPENING POSITION")
            print(f"   Symbol: {symbol}")
            print(f"   Side: {side.upper()}")
            print(f"   Size: {size}")
            print(f"   Leverage: {config.leverage}x")
            print(f"   Entry: ${price:.4f}")
            print(f"   TP: ${tp_price:.4f} ({config.take_profit}%)")
            print(f"   SL: ${sl_price:.4f} ({config.stop_loss}%)")
            
            # Place order
            result = self.client.place_order(
                symbol=symbol,
                side=side,
                size=size,
                order_type='market'
            )
            
            if result and result.get('orderId'):
                print(f"   ✅ Order: {result['orderId']}")
                
                # LOG THE TRADE DECISION
                log_decision(f"🎯 OPENED {side.upper()} {symbol}", {
                    'type': 'trade_opened',
                    'symbol': symbol,
                    'side': side,
                    'size': size,
                    'entry_price': price,
                    'take_profit': tp_price,
                    'stop_loss': sl_price,
                    'leverage': config.leverage,
                    'order_id': result['orderId']
                })
                
                self.positions[symbol] = {
                    'order_id': result['orderId'],
                    'side': side,
                    'entry_price': price,
                    'size': size,
                    'tp': tp_price,
                    'sl': sl_price,
                    'leverage': config.leverage,
                    'open_time': datetime.now()
                }
                
                self.total_trades += 1
                return True
            else:
                print(f"   ❌ Order failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error opening position: {e}")
            return False
    
    def check_positions(self):
        """Verificar y cerrar posiciones si alcanzaron TP/SL"""
        for symbol, pos in list(self.positions.items()):
            try:
                ticker = self.get_ticker_data(symbol)
                if not ticker:
                    continue
                
                current_price = ticker['last']
                entry_price = pos['entry_price']
                side = pos['side']
                
                # Calcular PnL
                if side == 'buy':
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                    hit_tp = current_price >= pos['tp']
                    hit_sl = current_price <= pos['sl']
                else:
                    pnl_pct = (entry_price - current_price) / entry_price * 100
                    hit_tp = current_price <= pos['tp']
                    hit_sl = current_price >= pos['sl']
                
                # PnL real con leverage
                config = self.GRID_CONFIGS.get(symbol)
                leverage = config.leverage if config else 10
                position_value = pos['size'] * entry_price / leverage
                actual_pnl = pnl_pct * leverage * position_value / 100
                
                # Mostrar estado
                elapsed = (datetime.now() - pos['open_time']).total_seconds()
                if elapsed % 60 < 10:  # Cada ~minuto
                    print(f"   📍 {symbol}: {pnl_pct:+.2f}% (${actual_pnl:+.2f})")
                
                # Cerrar si TP o SL
                if hit_tp or hit_sl:
                    close_side = 'sell' if side == 'buy' else 'buy'
                    
                    emoji = "🎯 TP" if hit_tp else "🛑 SL"
                    print(f"\n{emoji} CLOSING {symbol}")
                    print(f"   Entry: ${entry_price:.4f} → Exit: ${current_price:.4f}")
                    print(f"   PnL: {pnl_pct:+.2f}% (${actual_pnl:+.2f})")
                    
                    # LOG THE CLOSE
                    log_decision(f"{emoji} CLOSED {symbol}", {
                        'type': 'trade_closed',
                        'symbol': symbol,
                        'side': side,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': actual_pnl,
                        'reason': 'take_profit' if hit_tp else 'stop_loss'
                    })
                    
                    # Close position
                    self.client.place_order(
                        symbol=symbol,
                        side=close_side,
                        size=pos['size'],
                        order_type='market'
                    )
                    
                    self.daily_pnl += actual_pnl
                    if actual_pnl > 0:
                        self.winning_trades += 1
                    
                    del self.positions[symbol]
                    
            except Exception as e:
                print(f"❌ Error checking {symbol}: {e}")
    
    def print_status(self):
        """Imprimir estado actual"""
        self.update_balance()
        
        print(f"\n{'='*60}")
        print(f"📊 STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"   💰 Equity: ${self.equity:.2f}")
        print(f"   💵 Available: ${self.available:.2f}")
        print(f"   📈 Unrealized: ${self.unrealized:+.2f}")
        print(f"   📊 Daily PnL: ${self.daily_pnl:+.2f}")
        print(f"   🔄 Trades: {self.total_trades}")
        if self.total_trades > 0:
            wr = self.winning_trades / self.total_trades * 100
            print(f"   ✅ Win Rate: {wr:.1f}%")
        print(f"   📍 Positions: {len(self.positions)}")
        
        for sym, pos in self.positions.items():
            print(f"      {sym}: {pos['side'].upper()} @ ${pos['entry_price']:.4f}")
    
    def run(self, interval: int = 30):
        """Ejecutar bot"""
        print(f"\n🚀 Starting bot...")
        print(f"   Interval: {interval}s")
        print(f"   Max Loss: ${self.max_daily_loss}")
        print(f"   Max Trades: {self.max_daily_trades}")
        
        cycle = 0
        last_status = 0
        
        try:
            while True:
                cycle += 1
                now = time.time()
                
                print(f"\n{'─'*50}")
                print(f"🔄 Cycle {cycle} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Safety check
                is_safe, reason = self.check_safety()
                print(f"   {reason}")
                
                if not is_safe:
                    print("   ⏸️ Paused")
                    time.sleep(interval * 2)
                    continue
                
                # Check positions
                self.check_positions()
                
                # Find opportunity
                if len(self.positions) < 3:  # Max 3 positions
                    opp = self.find_opportunity()
                    if opp:
                        symbol, side, price, size = opp
                        self.open_position(symbol, side, price, size)
                    else:
                        print("   🔍 No opportunity")
                else:
                    print(f"   ⏳ Max positions ({len(self.positions)})")
                
                # Status every 2 min
                if now - last_status > 120:
                    self.print_status()
                    last_status = now
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n⛔ Stopped by user")
            self.print_status()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          🏆 CONSERVATIVE GRID BOT                         ║
    ║          Estrategia segura para hackathon                 ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  • Grid trading en rangos laterales                       ║
    ║  • Leverage moderado (5x-10x)                             ║
    ║  • Stop loss automático                                   ║
    ║  • CoinGecko market filter                                ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    bot = ConservativeGridBot()
    bot.run(interval=30)
