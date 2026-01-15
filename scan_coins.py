"""
📊 Análisis de Movimiento de Monedas
Escanea todas las monedas y muestra oportunidades
"""

import requests
import time
from datetime import datetime

BASE_URL = "https://api-contract.weex.com"
COINS = [
    "cmt_dogeusdt", 
    "cmt_solusdt", 
    "cmt_adausdt",
    "cmt_ltcusdt",
    "cmt_ethusdt", 
    "cmt_bnbusdt", 
    "cmt_btcusdt"
]


def get_ticker(symbol):
    try:
        resp = requests.get(f"{BASE_URL}/capi/v2/market/ticker?symbol={symbol}", timeout=10)
        return resp.json()
    except:
        return {}


def get_candles(symbol, limit=50):
    try:
        resp = requests.get(
            f"{BASE_URL}/capi/v2/market/candles",
            params={"symbol": symbol, "granularity": "5m", "limit": str(limit)},
            timeout=10
        )
        return resp.json()
    except:
        return []


def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def main():
    print("\n" + "="*70)
    print("   📊 ANÁLISIS DE MOVIMIENTO DE MONEDAS - WEEX AI HACKATHON")
    print("="*70)
    print(f"   ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    
    for symbol in COINS:
        try:
            ticker = get_ticker(symbol)
            candles = get_candles(symbol)
            
            price = float(ticker.get('last', 0))
            high = float(ticker.get('high_24h', price))
            low = float(ticker.get('low_24h', price))
            
            # RSI
            if candles and isinstance(candles, list):
                prices = [float(c[4]) for c in candles if isinstance(c, list) and len(c) > 4]
                rsi = calc_rsi(prices)
            else:
                rsi = 50
            
            # Volatilidad
            rango = high - low
            vol = (rango / price * 100) if price > 0 else 0
            
            # Posición en rango (0-100)
            if rango > 0:
                pos_rango = ((price - low) / rango) * 100
            else:
                pos_rango = 50
            
            coin = symbol.replace('cmt_', '').replace('usdt', '').upper()
            
            # Determinar señal
            signal_strength = 0
            if rsi > 75:
                signal = "🔴 SHORT!"
                signal_strength = (rsi - 70) * 3
            elif rsi > 70:
                signal = "🟡 short?"
                signal_strength = (rsi - 70) * 2
            elif rsi < 25:
                signal = "🟢 LONG!"
                signal_strength = (30 - rsi) * 3
            elif rsi < 30:
                signal = "🟡 long?"
                signal_strength = (30 - rsi) * 2
            else:
                signal = "⚪ neutral"
                signal_strength = 0
            
            results.append({
                'coin': coin,
                'symbol': symbol,
                'price': price,
                'high': high,
                'low': low,
                'rsi': rsi,
                'vol': vol,
                'pos_rango': pos_rango,
                'signal': signal,
                'strength': min(signal_strength, 100)
            })
            
            time.sleep(0.2)
            
        except Exception as e:
            print(f"Error {symbol}: {e}")
    
    # Ordenar por volatilidad
    results.sort(key=lambda x: x['vol'], reverse=True)
    
    # Mostrar tabla
    print("\n┌" + "─"*68 + "┐")
    print("│ COIN  │    PRECIO    │  RSI  │  VOL  │ POS.RANGO │    SEÑAL    │")
    print("├" + "─"*68 + "┤")
    
    for r in results:
        coin = r['coin']
        price = r['price']
        rsi = r['rsi']
        vol = r['vol']
        pos = r['pos_rango']
        signal = r['signal']
        
        # Formato de precio
        if price > 1000:
            price_str = f"${price:>10,.0f}"
        elif price > 1:
            price_str = f"${price:>10,.2f}"
        else:
            price_str = f"${price:>10,.4f}"
        
        # Barra de posición en rango
        bar = "█" * int(pos / 10) + "░" * (10 - int(pos / 10))
        
        print(f"│ {coin:>4}  │ {price_str} │ {rsi:>5.1f} │ {vol:>4.1f}% │ [{bar}] │ {signal:<11} │")
    
    print("└" + "─"*68 + "┘")
    
    # Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN DE OPORTUNIDADES")
    print("="*70)
    
    overbought = [r for r in results if r['rsi'] > 70]
    oversold = [r for r in results if r['rsi'] < 30]
    high_vol = [r for r in results if r['vol'] > 3]
    
    if overbought:
        print("\n🔴 SOBRECOMPRADAS (oportunidad SHORT):")
        for r in overbought:
            print(f"   • {r['coin']}: RSI {r['rsi']:.1f} | Precio ${r['price']:,.4f}")
            print(f"     SL sugerido: ${r['price'] * 1.02:,.4f} | TP: ${r['price'] * 0.97:,.4f}")
    
    if oversold:
        print("\n🟢 SOBREVENDIDAS (oportunidad LONG):")
        for r in oversold:
            print(f"   • {r['coin']}: RSI {r['rsi']:.1f} | Precio ${r['price']:,.4f}")
            print(f"     SL sugerido: ${r['price'] * 0.98:,.4f} | TP: ${r['price'] * 1.03:,.4f}")
    
    if high_vol:
        print(f"\n🔥 MÁS VOLÁTILES HOY: {', '.join([r['coin'] for r in high_vol[:3]])}")
    
    if not overbought and not oversold:
        print("\n⚪ MERCADO NEUTRAL")
        print("   No hay señales fuertes en este momento.")
        print("   El Peak Hunter automático esperará hasta detectar RSI > 70 o < 30")
        
        # Mostrar las más cercanas
        closest_high = max(results, key=lambda x: x['rsi'])
        closest_low = min(results, key=lambda x: x['rsi'])
        
        print(f"\n   Más cerca de SHORT: {closest_high['coin']} (RSI: {closest_high['rsi']:.1f})")
        print(f"   Más cerca de LONG:  {closest_low['coin']} (RSI: {closest_low['rsi']:.1f})")
    
    print("\n" + "="*70)
    print("💡 INTERPRETACIÓN:")
    print("   • RSI > 70: Sobrecomprado → Peak Hunter abrirá SHORT")
    print("   • RSI < 30: Sobrevendido → Peak Hunter abrirá LONG")
    print("   • VOL alta: Mayor potencial de ganancias (y riesgos)")
    print("   • POS.RANGO: Posición actual entre mínimo-máximo 24h")
    print("="*70)


if __name__ == "__main__":
    main()
