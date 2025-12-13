# -*- coding: utf-8 -*-
"""
DOUBLE SLIT EXPERIMENT (SIM LAB)

Toy simulation of an interference pattern.
Does NOT affect trading; purely a lab process
that writes conceptual data to a log file.
"""

import math
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\godbrain-quantum")
LOG_DIR = ROOT / "logs"
DSLIT_LOG = LOG_DIR / "double_slit_experiment.log"


def safe_mkdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def simulate_interference(step_count: int = 64):
    """
    Simple interference pattern:
    I(x) = I0 * (cos(kx/2))^2
    """
    pattern = []
    for i in range(step_count):
        x = (i / (step_count - 1)) * 4.0 * math.pi - 2.0 * math.pi
        intensity = (math.cos(x / 2.0) ** 2)
        pattern.append((x, intensity))
    return pattern


def main():
    safe_mkdir(LOG_DIR)
    print("===============================================")
    print("   🔬 DOUBLE SLIT EXPERIMENT ONLINE            ")
    print("   Generating conceptual interference logs...  ")
    print("===============================================")

    iteration = 0

    while True:
        iteration += 1
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        pattern = simulate_interference()

        with DSLIT_LOG.open("a", encoding="utf-8") as f:
            f.write("===========================================\n")
            f.write(f"[DOUBLE SLIT] {ts} | iteration={iteration}\n")
            for x, inten in pattern:
                f.write(f"x={x:.3f}, I={inten:.4f}\n")

        print(f"[DOUBLE SLIT] Iteration {iteration} logged.")
        time.sleep(5)


if __name__ == "__main__":
    main()
