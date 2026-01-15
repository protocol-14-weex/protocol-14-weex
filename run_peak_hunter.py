"""
🎯 PEAK HUNTER AUTOMÁTICO
Monitorea monedas volátiles y ejecuta trades cuando señal > 70%

Configuración:
- Monedas: SOL, ETH, BNB, DOGE, ADA, LTC
- Monto: $15 x 10x = $150 exposición
- Stop Loss: 2%
- Take Profit: 3%
- Señal mínima: 70%
"""

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# API Config
API_KEY = os.getenv("WEEX_API_KEY")
SECRET_KEY = os.getenv("WEEX_SECRET_KEY")
PASSPHRASE = os.getenv("WEEX_PASSPHRASE")
BASE_URL = "https://api-contract.weex.com"

# =================== CONFIGURACIÓN ===================
TRADE_SIZE_USD = 15        # Monto por trade
LEVERAGE = 10              # Apalancamiento
MIN_SIGNAL_STRENGTH = 50   # Señal mínima para ejecutar (%) - bajado para más oportunidades
STOP_LOSS_PCT = 2.0        # Stop Loss %
TAKE_PROFIT_PCT = 3.0      # Take Profit %
SCAN_INTERVAL = 30         # Segundos entre escaneos
MAX_DAILY_TRADES = 50      # Máximo trades por día (aumentado)
MAX_DAILY_LOSS = 100       # Máximo pérdida diaria USD (aumentado)

# Monedas a monitorear (sin BTC que está en Grid)
MONITORED_COINS = [
    "cmt_solusdt",     # SOL 🔥
    "cmt_ethusdt",     # ETH 
    "cmt_bnbusdt",     # BNB
    "cmt_dogeusdt",    # DOGE 🔥
    "cmt_adausdt",     # ADA
    "cmt_ltcusdt",     # LTC
]

# Archivo de log para dashboard
TRADES_LOG = "peak_trades.json"


@dataclass
class Trade:
    """Registro de un trade ejecutado"""
    id: str
    timestamp: str
    symbol: str
    action: str          # 'long' o 'short'
    entry_price: float
    size: float
    size_usd: float
    leverage: int
    stop_loss: float
    take_profit: float
    signal_strength: float
    rsi: float
    status: str          # 'open', 'closed_tp', 'closed_sl', 'closed_manual'
    pnl: float = 0.0
    exit_price: float = 0.0
    closed_at: str = ""


class PeakHunterAuto:
    """
    Peak Hunter con ejecución automática de trades
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.trades_today: List[Trade] = []
        self.daily_pnl = 0.0
        self.last_trade_time = {}  # Para cooldown por moneda
        self.trade_cooldown = 300  # 5 min cooldown por moneda
        
        # Cargar trades previos
        self._load_trades()
        
        print("\n" + "="*60)
        print("🎯 PEAK HUNTER AUTOMÁTICO")
        print("="*60)
        print(f"📊 Configuración:")
        print(f"   💰 Monto: ${TRADE_SIZE_USD} x {LEVERAGE}x = ${TRADE_SIZE_USD * LEVERAGE}")
        print(f"   🛑 Stop Loss: {STOP_LOSS_PCT}%")
        print(f"   🎯 Take Profit: {TAKE_PROFIT_PCT}%")
        print(f"   📈 Señal mínima: {MIN_SIGNAL_STRENGTH}%")
        print(f"   ⏱️ Escaneo cada: {SCAN_INTERVAL}s")
        print(f"   🪙 Monedas: {', '.join([s.replace('cmt_', '').replace('usdt', '').upper() for s in MONITORED_COINS])}")
        print("="*60)
    
    def _load_trades(self):
        """Cargar trades del día desde archivo"""
        try:
            if os.path.exists(TRADES_LOG):
                with open(TRADES_LOG, 'r') as f:
                    data = json.load(f)
                    today = datetime.now().strftime("%Y-%m-%d")
                    # Solo cargar trades de hoy
                    self.trades_today = [
                        Trade(**t) for t in data.get('trades', [])
                        if t.get('timestamp', '').startswith(today)
                    ]
                    self.daily_pnl = sum(t.pnl for t in self.trades_today)
        except Exception as e:
            print(f"⚠️ No se pudo cargar historial: {e}")
            self.trades_today = []
    
    def _save_trades(self):
        """Guardar trades al archivo para dashboard"""
        try:
            data = {
                'updated': datetime.now().isoformat(),
                'daily_pnl': self.daily_pnl,
                'total_trades': len(self.trades_today),
                'trades': [asdict(t) for t in self.trades_today]
            }
            with open(TRADES_LOG, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando trades: {e}")
    
    def _sign(self, method: str, path: str, query: str = "", body: str = "") -> tuple:
        """Generar firma para API"""
        ts = str(int(time.time() * 1000))
        msg = ts + method + path + query + body
        sig = base64.b64encode(
            hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
        ).decode()
        return ts, sig
    
    def _headers(self, ts: str, sig: str) -> dict:
        return {
            "ACCESS-KEY": API_KEY,
            "ACCESS-SIGN": sig,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json"
        }
    
    def get_ticker(self, symbol: str) -> Dict:
        """Obtener precio actual"""
        try:
            resp = self.session.get(
                f"{BASE_URL}/capi/v2/market/ticker?symbol={symbol}",
                timeout=10
            )
            return resp.json()
        except:
            return {}
    
    def get_candles(self, symbol: str, limit: int = 50) -> List:
        """Obtener velas para RSI"""
        try:
            resp = self.session.get(
                f"{BASE_URL}/capi/v2/market/candles",
                params={"symbol": symbol, "granularity": "5m", "limit": str(limit)},
                timeout=10
            )
            return resp.json()
        except:
            return []
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcular RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def analyze_coin(self, symbol: str) -> Dict:
        """
        Analizar moneda y calcular señal
        
        Returns:
            Dict con análisis completo
        """
        result = {
            'symbol': symbol,
            'price': 0,
            'rsi': 50,
            'signal_strength': 0,
            'action': 'wait',
            'reason': ''
        }
        
        # Obtener precio
        ticker = self.get_ticker(symbol)
        if not ticker or not ticker.get('last'):
            return result
        
        price = float(ticker.get('last', 0))
        high_24h = float(ticker.get('high_24h', price))
        low_24h = float(ticker.get('low_24h', price))
        
        result['price'] = price
        
        # Calcular RSI
        candles = self.get_candles(symbol)
        if candles and isinstance(candles, list):
            prices = [float(c[4]) for c in candles if isinstance(c, list) and len(c) > 4]
            result['rsi'] = round(self.calculate_rsi(prices), 1)
        
        # Calcular cambios
        change_from_low = ((price - low_24h) / low_24h * 100) if low_24h > 0 else 0
        change_from_high = ((price - high_24h) / high_24h * 100) if high_24h > 0 else 0
        
        rsi = result['rsi']
        signal = 0
        reasons = []
        action = 'wait'
        
        # === DETECCIÓN SHORT (sobrecomprado) ===
        if rsi > 70:
            signal += 40
            reasons.append(f"RSI alto ({rsi})")
        if rsi > 80:
            signal += 20
            reasons.append("RSI extremo")
        
        if change_from_low > 5:
            signal += min(change_from_low * 3, 30)
            reasons.append(f"+{change_from_low:.1f}% desde mín")
        
        if price / high_24h > 0.98:  # Cerca del máximo
            signal += 15
            reasons.append("Cerca de máximo 24h")
        
        # === DETECCIÓN LONG (sobrevendido) ===
        if rsi < 30:
            signal += 40
            action = 'long'
            reasons.append(f"RSI bajo ({rsi})")
        if rsi < 20:
            signal += 20
            reasons.append("RSI extremo")
        
        if change_from_high < -5:
            signal += min(abs(change_from_high) * 3, 30)
            if action != 'long':
                action = 'long'
            reasons.append(f"{change_from_high:.1f}% desde máx")
        
        if price / low_24h < 1.02:  # Cerca del mínimo
            signal += 15
            if action != 'long':
                action = 'long'
            reasons.append("Cerca de mínimo 24h")
        
        # Determinar acción final
        if signal >= MIN_SIGNAL_STRENGTH:
            if rsi > 70:
                action = 'short'
            elif rsi < 30:
                action = 'long'
            # Si no es claro por RSI, usar cambio de precio
            elif change_from_low > 8:
                action = 'short'
            elif change_from_high < -8:
                action = 'long'
            else:
                action = 'wait'
        else:
            action = 'wait'
        
        result['signal_strength'] = min(signal, 100)
        result['action'] = action
        result['reason'] = ' | '.join(reasons) if reasons else 'Neutral'
        
        return result
    
    def place_order(self, symbol: str, action: str, signal: Dict) -> Optional[Trade]:
        """
        Ejecutar orden de compra/venta
        
        Args:
            symbol: Par de trading
            action: 'long' o 'short'
            signal: Datos del análisis
            
        Returns:
            Trade si se ejecutó exitosamente
        """
        # Verificar cooldown
        last_trade = self.last_trade_time.get(symbol, 0)
        if time.time() - last_trade < self.trade_cooldown:
            remaining = int(self.trade_cooldown - (time.time() - last_trade))
            print(f"   ⏳ Cooldown: {remaining}s restantes para {symbol}")
            return None
        
        # Verificar límites diarios
        if len(self.trades_today) >= MAX_DAILY_TRADES:
            print(f"   🛑 Límite de trades diarios alcanzado ({MAX_DAILY_TRADES})")
            return None
        
        if self.daily_pnl <= -MAX_DAILY_LOSS:
            print(f"   🛑 Límite de pérdida diaria alcanzado (-${MAX_DAILY_LOSS})")
            return None
        
        price = signal['price']
        
        # Calcular tamaño según moneda - CORREGIDO para step sizes
        position_value = TRADE_SIZE_USD * LEVERAGE
        
        if 'btc' in symbol:
            # BTC: stepSize 0.001
            size = round(position_value / price, 3)
        elif 'eth' in symbol:
            # ETH: stepSize 0.01
            size = round(position_value / price, 2)
        elif 'doge' in symbol:
            # DOGE: stepSize 100
            raw_size = position_value / price
            size = round(raw_size / 100) * 100  # Redondear a múltiplo de 100
            if size < 100:
                size = 100
        elif 'sol' in symbol:
            # SOL: stepSize 0.1
            raw_size = position_value / price
            size = round(raw_size * 10) / 10  # Redondear a 0.1
            if size < 0.1:
                size = 0.1
        elif 'bnb' in symbol:
            # BNB: stepSize 0.1
            raw_size = position_value / price
            size = round(raw_size * 10) / 10  # Redondear a 0.1
            if size < 0.1:
                size = 0.1
        elif 'ada' in symbol:
            # ADA: stepSize 10
            raw_size = position_value / price
            size = round(raw_size / 10) * 10  # Redondear a múltiplo de 10
            if size < 10:
                size = 10
        elif 'ltc' in symbol:
            # LTC: stepSize 0.1
            raw_size = position_value / price
            size = round(raw_size * 10) / 10
            if size < 0.1:
                size = 0.1
        else:
            size = round(position_value / price, 1)
            if size < 0.1:
                size = 0.1
        
        # Calcular SL y TP
        if action == 'long':
            sl_price = price * (1 - STOP_LOSS_PCT / 100)
            tp_price = price * (1 + TAKE_PROFIT_PCT / 100)
            order_type = "1"  # open_long
        else:  # short
            sl_price = price * (1 + STOP_LOSS_PCT / 100)
            tp_price = price * (1 - TAKE_PROFIT_PCT / 100)
            order_type = "2"  # open_short
        
        coin = symbol.replace('cmt_', '').replace('usdt', '').upper()
        action_emoji = "🟢" if action == 'long' else "🔴"
        
        print(f"\n{action_emoji} EJECUTANDO {action.upper()} en {coin}")
        print(f"   💰 Precio: ${price:,.4f}")
        print(f"   📦 Size: {size} (${TRADE_SIZE_USD} x {LEVERAGE}x)")
        print(f"   🛑 SL: ${sl_price:,.4f} ({STOP_LOSS_PCT}%)")
        print(f"   🎯 TP: ${tp_price:,.4f} ({TAKE_PROFIT_PCT}%)")
        print(f"   📊 Señal: {signal['signal_strength']}% | RSI: {signal['rsi']}")
        
        # Colocar orden
        path = "/capi/v2/order/placeOrder"
        
        body = {
            "symbol": symbol,
            "client_oid": f"peak_{action}_{int(time.time())}",
            "size": str(size),
            "type": order_type,
            "order_type": "0",     # Normal
            "match_price": "1",    # Market order
        }
        body_str = json.dumps(body)
        
        ts, sig = self._sign("POST", path, "", body_str)
        headers = self._headers(ts, sig)
        
        try:
            resp = requests.post(f"{BASE_URL}{path}", headers=headers, data=body_str, timeout=30)
            result = resp.json()
            
            if result.get('order_id'):
                print(f"   ✅ Order ID: {result['order_id']}")
                
                # Crear registro de trade
                trade = Trade(
                    id=result['order_id'],
                    timestamp=datetime.now().isoformat(),
                    symbol=symbol,
                    action=action,
                    entry_price=price,
                    size=size,
                    size_usd=TRADE_SIZE_USD,
                    leverage=LEVERAGE,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    signal_strength=signal['signal_strength'],
                    rsi=signal['rsi'],
                    status='open'
                )
                
                self.trades_today.append(trade)
                self.last_trade_time[symbol] = time.time()
                self._save_trades()
                
                # Intentar colocar TP/SL
                self._place_tp_sl(symbol, action, size, sl_price, tp_price)
                
                return trade
            else:
                msg = result.get('msg', result.get('message', str(result)))
                print(f"   ⚠️ Error: {msg}")
                return None
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return None
    
    def _place_tp_sl(self, symbol: str, action: str, size: float, sl_price: float, tp_price: float):
        """Colocar órdenes de Stop Loss y Take Profit"""
        
        # Tipo de cierre: close_long (3) o close_short (4)
        if action == 'long':
            close_type = "3"  # close_long
        else:
            close_type = "4"  # close_short
        
        # TP Order
        tp_body = {
            "symbol": symbol,
            "client_oid": f"tp_{int(time.time())}",
            "size": str(size),
            "type": close_type,
            "order_type": "0",
            "price": str(round(tp_price, 4)),
            "match_price": "0",
        }
        
        # SL Order  
        sl_body = {
            "symbol": symbol,
            "client_oid": f"sl_{int(time.time())}",
            "size": str(size),
            "type": close_type,
            "order_type": "0",
            "price": str(round(sl_price, 4)),
            "match_price": "0",
        }
        
        path = "/capi/v2/order/placeOrder"
        
        for name, body in [("TP", tp_body), ("SL", sl_body)]:
            try:
                body_str = json.dumps(body)
                ts, sig = self._sign("POST", path, "", body_str)
                headers = self._headers(ts, sig)
                resp = requests.post(f"{BASE_URL}{path}", headers=headers, data=body_str, timeout=30)
                result = resp.json()
                if result.get('order_id'):
                    print(f"   📍 {name} colocado: {result['order_id']}")
            except Exception as e:
                print(f"   ⚠️ Error colocando {name}: {e}")
    
    def check_positions(self):
        """Verificar posiciones abiertas y actualizar P&L"""
        path = "/capi/v2/position/positions"
        query = "?symbol=cmt_btcusdt"  # Endpoint requiere symbol
        
        ts, sig = self._sign("GET", path, query)
        headers = self._headers(ts, sig)
        
        try:
            # Verificar cada símbolo monitoreado
            for symbol in MONITORED_COINS:
                query = f"?symbol={symbol}"
                ts, sig = self._sign("GET", path, query)
                headers = self._headers(ts, sig)
                
                resp = requests.get(f"{BASE_URL}{path}{query}", headers=headers, timeout=10)
                data = resp.json()
                
                if data and isinstance(data, list):
                    for pos in data:
                        if float(pos.get('total', 0)) > 0:
                            pnl = float(pos.get('unrealizedPL', 0))
                            side = pos.get('holdSide', '')
                            coin = symbol.replace('cmt_', '').replace('usdt', '').upper()
                            
                            emoji = "🟢" if pnl >= 0 else "🔴"
                            print(f"   {emoji} {coin} {side}: P&L ${pnl:,.2f}")
        except Exception as e:
            pass  # Silenciar errores de posición
    
    def scan_and_trade(self):
        """Escanear todas las monedas y ejecutar trades si hay señales fuertes"""
        now = datetime.now()
        print(f"\n⏰ [{now.strftime('%H:%M:%S')}] Escaneando monedas...")
        print("-" * 50)
        
        opportunities = []
        
        for symbol in MONITORED_COINS:
            try:
                signal = self.analyze_coin(symbol)
                
                coin = symbol.replace('cmt_', '').replace('usdt', '').upper()
                
                # Mostrar estado
                if signal['action'] == 'wait':
                    emoji = "⚪"
                elif signal['action'] == 'long':
                    emoji = "🟢"
                else:
                    emoji = "🔴"
                
                strength = signal['signal_strength']
                bar = "█" * int(strength / 10) + "░" * (10 - int(strength / 10))
                
                # Código de color para señal
                if strength >= MIN_SIGNAL_STRENGTH:
                    strength_color = "🔥"
                elif strength >= 50:
                    strength_color = "🟡"
                else:
                    strength_color = ""
                
                print(f"{emoji} {coin:>5} | ${signal['price']:>10,.4f} | "
                      f"RSI: {signal['rsi']:>5.1f} | [{bar}] {strength:>5.1f}% {strength_color}")
                
                # Guardar oportunidades fuertes
                if strength >= MIN_SIGNAL_STRENGTH and signal['action'] != 'wait':
                    opportunities.append(signal)
                
                time.sleep(0.2)  # Rate limit
                
            except Exception as e:
                print(f"❌ Error {symbol}: {e}")
        
        # Ejecutar trades en oportunidades
        if opportunities:
            print("\n" + "🔥" * 20)
            print("   ¡SEÑALES FUERTES DETECTADAS!")
            print("🔥" * 20)
            
            # Ordenar por fuerza de señal
            opportunities.sort(key=lambda x: x['signal_strength'], reverse=True)
            
            for signal in opportunities:
                trade = self.place_order(signal['symbol'], signal['action'], signal)
                if trade:
                    time.sleep(1)  # Pequeña pausa entre trades
        else:
            print("\n⚪ No hay señales fuertes. Mercado neutral.")
        
        # Mostrar resumen
        print("\n📊 RESUMEN DEL DÍA:")
        print(f"   Trades ejecutados: {len(self.trades_today)}/{MAX_DAILY_TRADES}")
        print(f"   P&L acumulado: ${self.daily_pnl:,.2f}")
        
        # Verificar posiciones
        self.check_positions()
    
    def run(self):
        """Ejecutar loop principal de monitoreo"""
        print("\n🚀 Iniciando monitoreo continuo...")
        print(f"   Escaneando cada {SCAN_INTERVAL} segundos")
        print("   Presiona Ctrl+C para detener\n")
        
        try:
            while True:
                self.scan_and_trade()
                
                # Countdown visual
                print(f"\n⏳ Próximo escaneo en {SCAN_INTERVAL}s...")
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Peak Hunter detenido")
            print(f"   Total trades hoy: {len(self.trades_today)}")
            print(f"   P&L del día: ${self.daily_pnl:,.2f}")
            self._save_trades()


def main():
    """Punto de entrada"""
    print("\n" + "🎯" * 30)
    print("   PEAK HUNTER AUTOMÁTICO - WEEX AI HACKATHON")
    print("🎯" * 30)
    
    hunter = PeakHunterAuto()
    hunter.run()


if __name__ == "__main__":
    main()
