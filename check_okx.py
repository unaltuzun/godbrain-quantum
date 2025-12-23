# Quick OKX Balance & Position Check
import ccxt

okx = ccxt.okx({
    'apiKey': '7dc4071e-8f26-4e54-b130-4f20274cfbc2',
    'secret': '89F49B46868E7E8D8E5996A6FF84C5E1',
    'password': 'Godbrain123.',
})

print("=== OKX Account Status ===")

try:
    bal = okx.fetch_balance()
    print(f"USDT Total: ${bal['total'].get('USDT', 0):.2f}")
    print(f"USDT Free:  ${bal['free'].get('USDT', 0):.2f}")
    print(f"USDT Used:  ${bal['used'].get('USDT', 0):.2f}")
except Exception as e:
    print(f"Balance Error: {e}")

print("\n=== Open Positions ===")
try:
    positions = okx.fetch_positions()
    open_positions = [p for p in positions if float(p.get('contracts', 0) or 0) > 0]
    if open_positions:
        for p in open_positions:
            print(f"  {p['symbol']}: {p['contracts']} contracts @ ${p.get('entryPrice', 0)}")
            print(f"    Side: {p.get('side', 'N/A')}, PnL: ${p.get('unrealizedPnl', 0):.2f}")
    else:
        print("  No open positions")
except Exception as e:
    print(f"Position Error: {e}")
