#!/usr/bin/env python3
"""Cerrar todas las posiciones y órdenes"""

from weex_client import WeexClient

def main():
    client = WeexClient()
    
    print("="*50)
    print("🛑 CERRANDO TODO")
    print("="*50)
    
    # 1. Cancelar órdenes
    print("\n📋 Cancelando órdenes...")
    for sym in ['cmt_btcusdt', 'cmt_ethusdt', 'cmt_solusdt', 'cmt_ltcusdt', 'cmt_dogeusdt']:
        try:
            client.cancel_all_orders(sym)
            print(f"   {sym}: OK")
        except:
            pass
    
    # 2. Cerrar posiciones
    print("\n📍 Cerrando posiciones...")
    try:
        positions = client.get_positions()
        if positions:
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
                    order_id = result.get('orderId', 'N/A') if result else 'FAIL'
                    print(f"   ✅ Order: {order_id}")
        else:
            print("   ✅ No hay posiciones abiertas")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Balance final
    print("\n💰 Balance final:")
    try:
        assets = client.get_account_assets()
        if isinstance(assets, list):
            for a in assets:
                if a.get('coinName') == 'USDT':
                    equity = float(a.get('equity', 0))
                    available = float(a.get('available', 0))
                    unrealized = float(a.get('unrealizePnl', 0))
                    print(f"   Equity: ${equity:.2f}")
                    print(f"   Available: ${available:.2f}")
                    print(f"   Unrealized: ${unrealized:.2f}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ LISTO PARA MICRO SCALPER!")

if __name__ == "__main__":
    main()
