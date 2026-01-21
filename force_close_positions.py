#!/usr/bin/env python3
"""Forzar cierre de todas las posiciones"""

from weex_client import WeexClient
import time

def main():
    client = WeexClient()
    print("="*50)
    print("🛑 FORZANDO CIERRE DE POSICIONES")
    print("="*50)
    
    # Intentar varias veces
    for attempt in range(5):
        print(f"\n📍 Intento {attempt+1}/5...")
        try:
            positions = client.get_positions()
            
            if not positions:
                print("   ✅ No hay posiciones abiertas")
                break
            
            if isinstance(positions, list):
                for pos in positions:
                    symbol = pos.get('symbol', '')
                    side = pos.get('holdSide', '')
                    size = float(pos.get('total', 0))
                    
                    if size > 0:
                        close_side = 'sell' if side == 'long' else 'buy'
                        print(f"   Cerrando {symbol}: {side} {size}")
                        
                        result = client.place_order(
                            symbol=symbol,
                            side=close_side,
                            size=size,
                            order_type='market'
                        )
                        
                        if result and isinstance(result, dict):
                            order_id = result.get('orderId', 'N/A')
                            print(f"   ✅ Cerrado: {order_id}")
                        else:
                            print(f"   ⚠️ Resultado: {result}")
                        
                        time.sleep(1)
            else:
                print(f"   ⚠️ Respuesta inesperada: {positions}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(2)
    
    # Mostrar balance final
    print("\n💰 Balance final:")
    try:
        assets = client.get_account_assets()
        if isinstance(assets, list):
            for a in assets:
                if a.get('coinName') == 'USDT':
                    print(f"   Equity: ${float(a.get('equity', 0)):.2f}")
                    print(f"   Available: ${float(a.get('available', 0)):.2f}")
                    print(f"   Unrealized: ${float(a.get('unrealizePnl', 0)):.2f}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    main()
