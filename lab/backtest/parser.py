import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class TradeEvent:
    timestamp: datetime
    symbol: str
    action: str         # BUY, SELL
    size_usd: float
    regime: Optional[str]
    flow_mult: float
    raw_line: str

    @property
    def side(self) -> int:
        """Returns 1 for BUY, -1 for SELL logic."""
        return 1 if self.action.upper() in ["BUY", "STRONG_BUY"] else -1

class LogParser:
    # Örnek satır:
    # 2025-12-11T22:25:38.515601 |   >>> EXECUTE: SELL SOL/USDT:USDT | $15 | Regime:TRENDING_DOWN | Flow:1.00x | ...
    PATTERN = re.compile(
        r"^(?P<ts>[\d\-T:\.]+) \|.*>>> EXECUTE: (?P<action>\w+) (?P<symbol>[^ ]+) \| \$(?P<size>[\d\.]+) \| Regime:(?P<regime>[^ ]+) \| Flow:(?P<flow>[\d\.]+)x"
    )

    @staticmethod
    def parse_file(file_path: str) -> List[TradeEvent]:
        events: List[TradeEvent] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ">>> EXECUTE:" not in line:
                        continue

                    match = LogParser.PATTERN.search(line.strip())
                    if not match:
                        continue

                    data = match.groupdict()
                    ts_str = data["ts"]
                    try:
                        if "." in ts_str:
                            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
                        else:
                            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        # Eğer format çok egzotikse, direkt parse etmeyi boş ver
                        print(f"[PARSER] Bad timestamp format: {ts_str}")
                        continue

                    try:
                        event = TradeEvent(
                            timestamp=ts,
                            symbol=data["symbol"],
                            action=data["action"],
                            size_usd=float(data["size"]),
                            regime=data["regime"],
                            flow_mult=float(data["flow"]),
                            raw_line=line.strip()
                        )
                        events.append(event)
                    except Exception as e:
                        print(f"[PARSER] Skipped line due to error: {e} | Line: {line.strip()[:80]}...")
        except FileNotFoundError:
            print(f"[PARSER] File not found: {file_path}")
        return events
