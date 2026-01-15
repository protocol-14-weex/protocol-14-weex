"""
🎯 PEAK HUNTER - Detector de Picos para Shorts

Estrategia: Detectar monedas en picos (sobrecompradas) y hacer SHORT
cuando están a punto de caer.

Señales de PICO (oportunidad de SHORT):
- RSI > 75 (muy sobrecomprado)
- Subida > 8% en 24h
- Volumen anormal
- DeepSeek sentiment muy bullish (contrarian)

Monedas más volátiles: DOGE, SOL, XRP, ADA
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
from dataclasses import dataclass
from typing import List, Dict, Optional
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# API Config
API_KEY = os.getenv("WEEX_API_KEY")
SECRET_KEY = os.getenv("WEEX_SECRET_KEY")
PASSPHRASE = os.getenv("WEEX_PASSPHRASE")
BASE_URL = "https://api-contract.weex.com"

# Monedas ordenadas por volatilidad
VOLATILE_COINS = [
    "cmt_dogeusdt",  # 🔥 Más volátil
    "cmt_solusdt",   # 🔥 Muy volátil
    "cmt_xrpusdt",   # 🔥 Volátil
    "cmt_adausdt",   # 🟡 Media-alta
    "cmt_ltcusdt",   # 🟡 Media
    "cmt_ethusdt",   # 🟢 Estable
    "cmt_bnbusdt",   # 🟢 Estable
    "cmt_btcusdt",   # 🟢 Más estable
]


@dataclass
class PeakSignal:
    """Señal de pico detectada"""
    symbol: str
    current_price: float
    change_24h: float
    rsi: float
    signal_strength: float  # 0-100
    action: str  # 'short', 'long', 'wait'
    reason: str
    suggested_entry: float
    suggested_sl: float
    suggested_tp: float


class PeakHunter:
    """
    Detector de picos para trading de reversión
    """
    
    def __init__(self):
        self.session = requests.Session()
        
        # Configuración
        self.rsi_overbought = 70      # RSI para considerar sobrecomprado
        self.rsi_oversold = 30        # RSI para considerar sobrevendido
        self.change_threshold = 5     # % cambio mínimo para considerar
        self.min_signal_strength = 60 # Fuerza mínima para recomendar
    
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
        """Obtener precio y cambio 24h"""
        try:
            resp = self.session.get(
                f"{BASE_URL}/capi/v2/market/ticker?symbol={symbol}",
                timeout=10
            )
            return resp.json()
        except:
            return {}
    
    def get_candles(self, symbol: str, granularity: str = "5m", limit: int = 50) -> List:
        """Obtener velas para calcular RSI"""
        try:
            resp = self.session.get(
                f"{BASE_URL}/capi/v2/market/candles",
                params={"symbol": symbol, "granularity": granularity, "limit": str(limit)},
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
    
    def analyze_coin(self, symbol: str) -> Optional[PeakSignal]:
        """
        Analizar una moneda para detectar picos
        
        Returns:
            PeakSignal si hay oportunidad, None si no
        """
        # Obtener datos
        ticker = self.get_ticker(symbol)
        if not ticker or not ticker.get('last'):
            return None
        
        current_price = float(ticker.get('last', 0))
        high_24h = float(ticker.get('high_24h', current_price))
        low_24h = float(ticker.get('low_24h', current_price))
        
        # Calcular cambio 24h
        if low_24h > 0:
            change_from_low = ((current_price - low_24h) / low_24h) * 100
        else:
            change_from_low = 0
        
        if high_24h > 0:
            change_from_high = ((current_price - high_24h) / high_24h) * 100
        else:
            change_from_high = 0
        
        # Obtener RSI
        candles = self.get_candles(symbol)
        if candles and isinstance(candles, list):
            prices = [float(c[4]) for c in candles if isinstance(c, list) and len(c) > 4]
            rsi = self.calculate_rsi(prices)
        else:
            rsi = 50
        
        # Calcular fuerza de señal
        signal_strength = 0
        reasons = []
        action = "wait"
        
        # === DETECCIÓN DE PICO (oportunidad SHORT) ===
        if rsi > self.rsi_overbought:
            signal_strength += 40
            reasons.append(f"RSI sobrecomprado ({rsi:.1f})")
        
        if change_from_low > self.change_threshold:
            bonus = min(change_from_low * 3, 30)  # Max 30 puntos
            signal_strength += bonus
            reasons.append(f"Subió {change_from_low:.1f}% desde mínimo")
        
        # Cerca del máximo 24h = probable reversión
        if high_24h > 0:
            proximity_to_high = (current_price / high_24h) * 100
            if proximity_to_high > 98:  # Dentro del 2% del máximo
                signal_strength += 20
                reasons.append("Cerca del máximo 24h")
        
        # === DETECCIÓN DE VALLE (oportunidad LONG) ===
        if rsi < self.rsi_oversold:
            signal_strength += 40
            action = "long"
            reasons.append(f"RSI sobrevendido ({rsi:.1f})")
        
        if change_from_high < -self.change_threshold:
            bonus = min(abs(change_from_high) * 3, 30)
            signal_strength += bonus
            if action != "long":
                action = "long"
            reasons.append(f"Cayó {abs(change_from_high):.1f}% desde máximo")
        
        # Determinar acción final
        if signal_strength >= self.min_signal_strength:
            if rsi > self.rsi_overbought or change_from_low > 8:
                action = "short"
            elif rsi < self.rsi_oversold or change_from_high < -8:
                action = "long"
        else:
            action = "wait"
        
        # Calcular niveles
        if action == "short":
            suggested_entry = current_price
            suggested_sl = current_price * 1.02  # SL 2% arriba
            suggested_tp = current_price * 0.97  # TP 3% abajo
        elif action == "long":
            suggested_entry = current_price
            suggested_sl = current_price * 0.98  # SL 2% abajo
            suggested_tp = current_price * 1.03  # TP 3% arriba
        else:
            suggested_entry = current_price
            suggested_sl = 0
            suggested_tp = 0
        
        return PeakSignal(
            symbol=symbol,
            current_price=current_price,
            change_24h=change_from_low,
            rsi=round(rsi, 1),
            signal_strength=round(signal_strength, 1),
            action=action,
            reason=" | ".join(reasons) if reasons else "Sin señal clara",
            suggested_entry=suggested_entry,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp
        )
    
    def scan_all_coins(self) -> List[PeakSignal]:
        """
        Escanear todas las monedas permitidas
        
        Returns:
            Lista de señales ordenadas por fuerza
        """
        signals = []
        
        print("\n🔍 Escaneando monedas volátiles...")
        print("="*60)
        
        for symbol in VOLATILE_COINS:
            try:
                signal = self.analyze_coin(symbol)
                if signal:
                    signals.append(signal)
                    
                    # Mostrar resultado
                    emoji = "🔴" if signal.action == "short" else "🟢" if signal.action == "long" else "⚪"
                    strength_bar = "█" * int(signal.signal_strength / 10) + "░" * (10 - int(signal.signal_strength / 10))
                    
                    coin_name = symbol.replace("cmt_", "").replace("usdt", "").upper()
                    print(f"{emoji} {coin_name:>5} | ${signal.current_price:>10,.4f} | "
                          f"RSI: {signal.rsi:>5.1f} | "
                          f"[{strength_bar}] {signal.signal_strength:>5.1f}%")
                
                time.sleep(0.2)  # Rate limit
                
            except Exception as e:
                print(f"❌ Error {symbol}: {e}")
        
        # Ordenar por fuerza de señal
        signals.sort(key=lambda x: x.signal_strength, reverse=True)
        
        return signals
    
    def get_best_opportunity(self) -> Optional[PeakSignal]:
        """
        Obtener la mejor oportunidad actual
        """
        signals = self.scan_all_coins()
        
        # Filtrar solo señales accionables
        actionable = [s for s in signals if s.action in ['short', 'long'] and s.signal_strength >= self.min_signal_strength]
        
        if actionable:
            return actionable[0]
        return None
    
    def display_opportunities(self):
        """
        Mostrar todas las oportunidades detectadas
        """
        signals = self.scan_all_coins()
        
        print("\n" + "="*70)
        print("🎯 OPORTUNIDADES DETECTADAS")
        print("="*70)
        
        shorts = [s for s in signals if s.action == "short" and s.signal_strength >= 50]
        longs = [s for s in signals if s.action == "long" and s.signal_strength >= 50]
        
        if shorts:
            print("\n🔴 SHORTS (picos detectados):")
            for s in shorts:
                coin = s.symbol.replace("cmt_", "").replace("usdt", "").upper()
                print(f"   {coin}: ${s.current_price:,.4f}")
                print(f"      Fuerza: {s.signal_strength}% | RSI: {s.rsi}")
                print(f"      Razón: {s.reason}")
                print(f"      Entry: ${s.suggested_entry:,.4f} | SL: ${s.suggested_sl:,.4f} | TP: ${s.suggested_tp:,.4f}")
                print()
        
        if longs:
            print("\n🟢 LONGS (valles detectados):")
            for s in longs:
                coin = s.symbol.replace("cmt_", "").replace("usdt", "").upper()
                print(f"   {coin}: ${s.current_price:,.4f}")
                print(f"      Fuerza: {s.signal_strength}% | RSI: {s.rsi}")
                print(f"      Razón: {s.reason}")
                print(f"      Entry: ${s.suggested_entry:,.4f} | SL: ${s.suggested_sl:,.4f} | TP: ${s.suggested_tp:,.4f}")
                print()
        
        if not shorts and not longs:
            print("\n⚪ No hay señales fuertes en este momento.")
            print("   El mercado está en rango neutral.")
            print("   Espera a que una moneda haga un movimiento extremo.")
        
        print("="*70)
        
        return signals


class QuickShort:
    """
    Ejecutor rápido de shorts en picos
    """
    
    def __init__(self, hunter: PeakHunter):
        self.hunter = hunter
    
    def place_short(self, symbol: str, size_usd: float = 5, leverage: int = 10) -> Dict:
        """
        Colocar un short rápido
        
        Args:
            symbol: Par de trading
            size_usd: Monto en USD
            leverage: Apalancamiento
        """
        # Obtener precio actual
        ticker = self.hunter.get_ticker(symbol)
        price = float(ticker.get('last', 0))
        
        if price == 0:
            return {"error": "No se pudo obtener precio"}
        
        # Calcular tamaño
        position_value = size_usd * leverage
        
        # Determinar precisión según moneda
        if 'btc' in symbol:
            size = round(position_value / price, 4)
        elif 'eth' in symbol:
            size = round(position_value / price, 3)
        elif 'doge' in symbol:
            size = round(position_value / price, 0)
        else:
            size = round(position_value / price, 2)
        
        # Calcular SL y TP
        sl_price = price * 1.02  # 2% arriba
        tp_price = price * 0.97  # 3% abajo
        
        print(f"\n🔴 EJECUTANDO SHORT")
        print(f"   Symbol: {symbol}")
        print(f"   Price: ${price:,.4f}")
        print(f"   Size: {size} (${size_usd} x {leverage}x = ${position_value})")
        print(f"   SL: ${sl_price:,.4f} (+2%)")
        print(f"   TP: ${tp_price:,.4f} (-3%)")
        
        # Colocar orden
        ts = str(int(time.time() * 1000))
        path = "/capi/v2/order/placeOrder"
        
        body = {
            "symbol": symbol,
            "client_oid": f"short_{int(time.time())}",
            "size": str(size),
            "type": "2",           # 2 = open_short
            "order_type": "0",     # Normal
            "match_price": "1",    # Market order
        }
        body_str = json.dumps(body)
        
        msg = ts + "POST" + path + body_str
        sig = base64.b64encode(
            hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
        ).decode()
        
        headers = {
            "ACCESS-KEY": API_KEY,
            "ACCESS-SIGN": sig,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json"
        }
        
        resp = requests.post(f"{BASE_URL}{path}", headers=headers, data=body_str, timeout=30)
        result = resp.json()
        
        if result.get('order_id'):
            print(f"   ✅ Order ID: {result['order_id']}")
        else:
            print(f"   ⚠️ Response: {result}")
        
        return result


def main():
    """Ejecutar escáner de picos"""
    print("\n" + "🎯"*25)
    print("      PEAK HUNTER - Detector de Picos")
    print("🎯"*25)
    
    hunter = PeakHunter()
    hunter.display_opportunities()
    
    # Mostrar mejor oportunidad
    best = hunter.get_best_opportunity()
    if best:
        coin = best.symbol.replace("cmt_", "").replace("usdt", "").upper()
        print(f"\n🏆 MEJOR OPORTUNIDAD: {best.action.upper()} {coin}")
        print(f"   Precio: ${best.current_price:,.4f}")
        print(f"   Fuerza: {best.signal_strength}%")
        print(f"   RSI: {best.rsi}")
        
        print(f"\n💡 Para ejecutar (en Python):")
        print(f"   from strategies.peak_hunter import PeakHunter, QuickShort")
        print(f"   hunter = PeakHunter()")
        print(f"   short = QuickShort(hunter)")
        print(f"   short.place_short('{best.symbol}', size_usd=5, leverage=10)")


if __name__ == "__main__":
    main()
