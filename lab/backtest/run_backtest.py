import argparse
import sys
from pathlib import Path

# Proje root'unu path'e ekle (güvenlik için)
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.backtest.parser import LogParser
from lab.backtest.price_provider import CsvPriceProvider
from lab.backtest.metrics import run_metrics_engine

def main():
    parser = argparse.ArgumentParser(description="GODBRAIN v5 Backtest Runner")
    parser.add_argument("--log-file", required=True, help="Path to agg_decisions.log")
    parser.add_argument("--price-file", required=True, help="Path to historical prices CSV (timestamp,symbol,price)")
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=1000.0,
        help="Start equity for simulation"
    )

    args = parser.parse_args()

    print(f"\n[1/3] Parsing Logs: {args.log_file}")
    events = LogParser.parse_file(args.log_file)
    print(f"      Found {len(events)} execution events.")
    if not events:
        print("[ERR] No events found. Exiting.")
        return

    print(f"\n[2/3] Loading Prices: {args.price_file}")
    provider = CsvPriceProvider()
    provider.load_data(args.price_file)

    print(f"\n[3/3] Running Simulation (FIFO)...")
    report = run_metrics_engine(events, provider, initial_capital=args.initial_capital)

    print(report)
    print("\n--- PER SYMBOL ---")
    for sym, stats in report.per_symbol.items():
        print(f"{sym:<18} : PnL ${stats['pnl']:>8.2f} | Trades: {stats['trades']} | Wins: {stats['wins']}")

    print("\n[DONE] Backtest complete.")

if __name__ == "__main__":
    main()
