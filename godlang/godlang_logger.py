# godlang_logger.py
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO


class GodlangCSVLogger:
    """
    Simple CSV logger for quantum / godlang experiments.
    It auto-creates the file and header on first use.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.file: Optional[TextIO] = None
        self.writer: Optional[csv.writer] = None
        self._init_file()

    def _init_file(self) -> None:
        file_exists = self.path.exists()
        # newline="" is important for Windows CSV
        self.file = self.path.open("a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)

        if not file_exists:
            # Write header only once
            self.writer.writerow(["timestamp", "frequency", "amplitude", "probability"])
            self.file.flush()

    def log_sample(
        self,
        frequency: float,
        amplitude: float,
        probability: float,
        ts: Optional[datetime] = None,
    ) -> None:
        if self.writer is None or self.file is None:
            self._init_file()

        if ts is None:
            ts = datetime.now()

        self.writer.writerow(
            [
                ts.isoformat(timespec="seconds"),
                float(frequency),
                float(amplitude),
                float(probability),
            ]
        )
        # Flush so long-running experiments persist data
        self.file.flush()

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None
