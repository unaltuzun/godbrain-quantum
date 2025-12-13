#!/usr/bin/env bash
redis-cli SET godbrain:genetics:best_dna '[10, 10, 242, 331, 354, 500]'
redis-cli SET godbrain:genetics:best_meta '{"gen": 1039, "best_profit": 218867.5}'
python genetics/voltran_bridge.py --status
