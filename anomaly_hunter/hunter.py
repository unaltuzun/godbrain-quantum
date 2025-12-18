# -*- coding: utf-8 -*-
"""
GODBRAIN ANOMALY HUNTER - Main Module
7/24 Continuous anomaly monitoring
"""

import os
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

from . import Anomaly, NobelPotential, ContinuousLabInterface
from .detectors import (
    UniversalAttractorDetector,
    PhaseTransitionDetector,
    PowerLawDetector,
    QuantumSignatureDetector,
    SymmetryBreakingDetector,
    EntropyReversalDetector,
)


class AnomalyHunter:
    """
    Continuous Anomaly Hunter for Physics Lab.
    Monitors 7/24 evolution and hunts for Nobel-worthy discoveries.
    """
    
    def __init__(self):
        self.lab = ContinuousLabInterface()
        self.discoveries_dir = Path(__file__).parent.parent / "discoveries"
        self.discoveries_dir.mkdir(exist_ok=True)
        
        self.detectors = [
            UniversalAttractorDetector(),
            PhaseTransitionDetector(),
            PowerLawDetector(),
            QuantumSignatureDetector(),
            SymmetryBreakingDetector(),
            EntropyReversalDetector(),
        ]
        
        self.anomalies: List[Anomaly] = []
        self.scan_count = 0
    
    def scan(self) -> List[Anomaly]:
        """Perform one-time scan of all available data."""
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║        🔬 GODBRAIN ANOMALY HUNTER - SCANNING...                  ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        
        df = self.lab.get_all_metrics()
        current_gen = self.lab.get_current_generation()
        
        print(f"\n📊 Data: {len(df)} records, current generation: {current_gen}")
        print(f"🔍 Running {len(self.detectors)} detectors...\n")
        
        found_anomalies = []
        
        for detector in self.detectors:
            name = detector.__class__.__name__
            print(f"  → {name}...", end=" ")
            
            try:
                result = detector.detect(df)
                
                if result is None:
                    print("✗")
                elif isinstance(result, list):
                    if result:
                        print(f"✓ {len(result)} found!")
                        found_anomalies.extend(result)
                    else:
                        print("✗")
                else:
                    print("✓ FOUND!")
                    found_anomalies.append(result)
                    
            except Exception as e:
                print(f"⚠ Error: {e}")
        
        self.anomalies.extend(found_anomalies)
        self.scan_count += 1
        
        self._save_discoveries(found_anomalies)
        self._print_summary(found_anomalies)
        
        return found_anomalies
    
    async def monitor(self, interval_seconds: int = 300):
        """Continuously monitor for anomalies."""
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║     🔬 GODBRAIN ANOMALY HUNTER - CONTINUOUS MONITORING          ║")
        print("║                    Press Ctrl+C to stop                          ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        
        last_gen = 0
        
        while True:
            current_gen = self.lab.get_current_generation()
            
            if current_gen > last_gen:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Gen {last_gen} → {current_gen}")
                
                anomalies = self.scan()
                
                for anomaly in anomalies:
                    yield anomaly
                
                last_gen = current_gen
            
            await asyncio.sleep(interval_seconds)
    
    def _save_discoveries(self, anomalies: List[Anomaly]):
        """Save discoveries to disk."""
        for anomaly in anomalies:
            filename = self.discoveries_dir / f"{anomaly.id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(anomaly.to_dict(), f, indent=2, default=str)
    
    def _print_summary(self, anomalies: List[Anomaly]):
        """Print summary of findings."""
        print("\n" + "═" * 70)
        print("                        SCAN RESULTS")
        print("═" * 70)
        
        if not anomalies:
            print("\n  No anomalies detected. Evolution continues... 👀\n")
        else:
            print(f"\n  🎯 Found {len(anomalies)} anomalies!\n")
            
            by_potential = {}
            for a in anomalies:
                pot = a.nobel_potential.name
                by_potential.setdefault(pot, []).append(a)
            
            for potential in ['NOBEL_WORTHY', 'VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW']:
                if potential in by_potential:
                    print(f"  {'⭐' * NobelPotential[potential].value} {potential}:")
                    for a in by_potential[potential]:
                        print(f"      • {a.title}")
            
            nobel = [a for a in anomalies if a.nobel_potential == NobelPotential.NOBEL_WORTHY]
            if nobel:
                print("\n" + "🚨" * 20)
                print("  ⚠️  POTENTIAL NOBEL-WORTHY DISCOVERY!  ⚠️")
                print("🚨" * 20)
        
        print("\n" + "═" * 70)


def main():
    """Run anomaly hunter."""
    hunter = AnomalyHunter()
    hunter.scan()


async def monitor():
    """Run continuous monitoring."""
    hunter = AnomalyHunter()
    async for anomaly in hunter.monitor(interval_seconds=300):
        print("\n" + "🚨" * 10)
        print(anomaly)
        print("🚨" * 10 + "\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        asyncio.run(monitor())
    else:
        main()
