# ═══════════════════════════════════════════════════════════════════════════════
# GODBRAIN SYSTEM UPDATE DOCUMENTATION v2.0
# For: ChatGPT / Gemini Integration Context
# Date: 2024-12-09
# ═══════════════════════════════════════════════════════════════════════════════

## SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GODBRAIN QUANTUM v4.0                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SERAPH v2.0 (AI Code Architect)                   │   │
│  │  • Natural Language → Code Modifications                             │   │
│  │  • Auto-backup & Rollback                                            │   │
│  │  • Syntax Validation                                                 │   │
│  │  Location: /mnt/c/godbrain-quantum/seraph/seraph_v2.py              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 QUANTUM RESONANCE LAB v2.1                           │   │
│  │  • Multiverse Training (Genetic Algorithm)                           │   │
│  │  • DNA Academy Integration                                           │   │
│  │  • Resonance Bus Integration                                         │   │
│  │  Location: /mnt/c/godbrain-quantum/quantum_lab/                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │ DNA Academy   │  │ Resonance Bus │  │ Double Slit   │                   │
│  │ (Rankings)    │  │ (State Sync)  │  │ (Simulation)  │                   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘                   │
│          └──────────────────┴──────────────────┘                           │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      ULTIMATE PACK v2.0                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │   Regime    │  │   Signal    │  │    Data     │                  │   │
│  │  │  Detector   │  │   Filter    │  │   Feeds     │                  │   │
│  │  │ (Anti-WS)   │  │ (Anti-WS)   │  │  (Unified)  │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PM2 SERVICES (Production)                         │   │
│  │  • godbrain-chronos   (Chronos TRNG)                                │   │
│  │  • godbrain-quantum   (Main Aggregator)                             │   │
│  │  • godmoney-apex      (Execution Engine)                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## FILE STRUCTURE

```
/mnt/c/godbrain-quantum/
├── seraph/
│   ├── seraph_v2.py              # AI Code Architect (NEW)
│   ├── backups/                  # Auto-backups before modifications
│   └── patch_history.json        # Modification history
│
├── quantum_lab/
│   ├── quantum_resonance_lab_v2.py  # Multiverse Training Engine (NEW)
│   ├── universes/                # Generated market simulations
│   ├── convergence/              # Training convergence data
│   └── wisdom/                   # Extracted optimal parameters
│
├── ultimate_pack/
│   ├── regime/
│   │   └── regime_detector.py    # Anti-Whipsaw Regime Detection
│   ├── filters/
│   │   └── signal_filter.py      # Trade Signal Filtering (NEW)
│   ├── feeds/
│   │   └── data_feeds.py         # Unified Data Feeds
│   └── ultimate_connector.py     # Main Integration Point
│
├── dna_engine_academy.py         # DNA Evolution + Ranking (EXISTING)
├── resonance_bus.py              # Inter-module Communication (EXISTING)
├── double_slit_experiment.py     # Simulation Lab (EXISTING)
├── agg.py                        # Main Aggregator Entry Point
├── human_bias.json               # Risk Mode Config
└── human_control.json            # Kill Switch / Limits
```

## NEW MODULE: SERAPH v2.0 (AI Code Architect)

### Purpose
Self-modifying code agent that translates natural language commands into code changes.

### Key Classes

```python
# seraph/seraph_v2.py

class CommandType(Enum):
    CONFIG_UPDATE = "config_update"      # JSON config changes
    CODE_MODIFY = "code_modify"          # Modify existing code
    CODE_INJECT = "code_inject"          # Add new code
    FILE_CREATE = "file_create"          # Create new file
    MODULE_PATCH = "module_patch"        # Patch ultimate pack
    SYSTEM_COMMAND = "system_command"    # PM2 restart etc
    QUERY = "query"                      # Information query

@dataclass
class SeraphCommand:
    command_type: CommandType
    target_file: Optional[str] = None
    target_function: Optional[str] = None
    action: Optional[str] = None          # replace|insert_before|insert_after|append
    code_changes: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    confidence: float = 0.0
    requires_restart: bool = False

class BackupManager:
    """Auto-backup before any modification"""
    def create_backup(self, file_path: Path, patch_id: str) -> Path
    def rollback(self, patch_id: str) -> Tuple[bool, str]
    def get_recent_patches(self, count: int) -> List[dict]

class CodeModifier:
    """Handles actual code modifications"""
    def modify_file(self, command: SeraphCommand) -> PatchResult
    def create_file(self, command: SeraphCommand) -> PatchResult
    def update_config(self, command: SeraphCommand) -> PatchResult
```

### Usage Example

```python
# User says: "COOLDOWN_SEC = 300 satırını COOLDOWN_SEC = 600 yap"
# Seraph parses to:
{
    "command_type": "code_modify",
    "target_file": "ultimate_pack/regime/regime_detector.py",
    "action": "replace",
    "code_changes": "COOLDOWN_SEC = 600",
    "parameters": {"search_pattern": "COOLDOWN_SEC = 300"},
    "confidence": 0.95,
    "requires_restart": true
}
```

### API Configuration

```bash
# .env file
SERAPH_LLM_KEY=sk-ant-api03-xxxxx
SERAPH_LLM_MODEL=claude-sonnet-4-20250514
```

---

## NEW MODULE: QUANTUM RESONANCE LAB v2.1

### Purpose
Multiverse training engine that evolves trading strategies across simulated market conditions.

### Integration Points

```python
# quantum_lab/quantum_resonance_lab_v2.py

# Imports existing modules
from dna_engine_academy import DNAAcademy, DNAStrategyParams, GenomeRecord
from resonance_bus import ResonanceBus, ResonanceState

# Checks on startup:
# ✅ DNA Engine Academy - Genom ranking sistemi aktif
# ✅ Resonance Bus - Quantum state sinyalleri aktif  
# ✅ Double Slit Experiment - Interference log bulundu
```

### Key Classes

```python
class UniverseType(Enum):
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    BLACK_SWAN = "black_swan"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    FLASH_CRASH = "flash_crash"
    PUMP_DUMP = "pump_dump"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"

@dataclass
class StrategyGene:
    """Compatible with DNA Academy format"""
    # Regime Detection
    regime_cooldown: int = 300
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # Position Sizing (DNA Academy compatible)
    stop_loss_pct: float = -2.0
    take_profit_pct: float = 4.0
    position_size_factor: float = 0.15
    
    # Anti-Whipsaw
    min_trade_interval: int = 120
    reversal_cooldown: int = 300
    max_reversals_per_hour: int = 3
    consecutive_signals_required: int = 3
    
    def to_dna_academy_format(self) -> dict:
        """Convert to DNA Academy compatible format"""
        return {
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "rsi_buy_level": self.rsi_oversold,
            "rsi_sell_level": self.rsi_overbought,
            "position_size_factor": self.position_size_factor,
        }

class GeneticOptimizer:
    """Genetic algorithm engine"""
    population_size: int = 100
    elite_count: int = 10
    
    def initialize_population(self)
    def evaluate_population(self, universes) -> List[Tuple[StrategyGene, float]]
    def evolve(self, ranked) -> List[StrategyGene]

class MultiverseEngine:
    """Main training orchestrator"""
    def generate_universes(self, count_per_type: int, duration_days: int)
    def train(self, generations: int) -> ConvergedWisdom
    
    # During training, syncs with DNA Academy:
    if _existing_academy and best_gene:
        genome_id = hashlib.md5(str(best_gene.to_dict()).encode()).hexdigest()[:8]
        _existing_academy.record_cycle(
            genome_id=genome_id,
            family="QUANTUM_LAB_ELITE",
            equity_change_pct=best_fitness / 10,
            trades_in_cycle=10
        )
```

### Output: ConvergedWisdom

```python
@dataclass
class ConvergedWisdom:
    timestamp: datetime
    generations_trained: int
    universes_simulated: int
    best_fitness: float
    best_gene: StrategyGene
    optimal_ranges: Dict[str, Tuple[float, float]]
    recommended_changes: List[Dict[str, Any]]  # → Seraph commands
    academy_rank: str = "CADET"  # From DNA Academy
    academy_score: float = 0.0
```

---

## ANTI-WHIPSAW SYSTEM

### Problem Solved
Regime flip-flop every 10-30 seconds causing commission bleed.

### Solution Components

#### 1. Regime Detector (regime_detector.py)

```python
class RegimeDetector:
    # Anti-Whipsaw Config
    COOLDOWN_SEC = 600  # 10 minutes (was 300)
    
    def analyze(self, ohlcv_df: pd.DataFrame) -> RegimeSignal:
        # ... indicator calculation ...
        
        # Anti-Whipsaw: Cooldown Logic
        time_diff = (datetime.now() - self.regime_start_time).total_seconds()
        if regime != self.current_regime:
            if time_diff < self.COOLDOWN_SEC and regime != RegimeType.CRISIS:
                # Force stick to old regime if cooldown active
                regime = self.current_regime
                confidence *= 0.5
            else:
                self.current_regime = regime
                self.regime_start_time = datetime.now()
```

#### 2. Signal Filter (signal_filter.py) - NEW

```python
class SignalFilter:
    MIN_SECONDS_BETWEEN_TRADES = 120    # 2 minutes
    MIN_SECONDS_FOR_REVERSAL = 300      # 5 minutes
    MIN_CONVICTION_THRESHOLD = 0.5
    MAX_TRADES_PER_HOUR = 10
    MAX_REVERSALS_PER_HOUR = 3
    
    def filter(self, action: str, conviction: float, regime: str) -> FilteredSignal:
        # 1. HOLD actions pass through
        # 2. Conviction threshold check
        # 3. Minimum time between trades
        # 4. Reversal restrictions
        # 5. Trade rate limiting
        # 6. Same direction boost
        
    def record_trade(self, direction: str):
        """Must be called after execution"""
```

#### 3. Integration in agg.py

```python
from ultimate_pack.filters.signal_filter import SignalFilter

signal_filter = SignalFilter()

# In main loop:
if decision.action in ['STRONG_BUY', 'BUY']:
    raw_action = 'BUY'
elif decision.action in ['STRONG_SELL', 'SELL']:
    raw_action = 'SELL'
else:
    raw_action = 'HOLD'

# Apply filter
filtered = signal_filter.filter(raw_action, decision.conviction)

if filtered.should_execute:
    # Execute trade...
    signal_filter.record_trade(filtered.filtered_action)
else:
    print(f"[BLOCKED] {filtered.filter_reason}")
```

---

## EXISTING MODULES REFERENCE

### DNA Engine Academy (dna_engine_academy.py)

```python
@dataclass
class DNAStrategyParams:
    stop_loss_pct: float      # e.g. -0.57 => -0.57%
    take_profit_pct: float    # e.g. 23.1 => +23.1%
    rsi_buy_level: float      # 0-100
    rsi_sell_level: float     # 0-100
    position_size_factor: float  # 0-1

class DNAEvolutionEngine:
    def evolve(self, current: DNAStrategyParams, equity_change_pct: float, 
               env: MarketEnv) -> Tuple[DNAStrategyParams, str]

class DNAAcademy:
    """Ranks: CADET → ROOKIE → SPECIALIST → EXPERT → MASTER → DOCTOR"""
    def record_cycle(self, genome_id, family, equity_change_pct, ...)
    def leaderboard(self, top_n: int) -> List[GenomeRecord]
```

### Resonance Bus (resonance_bus.py)

```python
ResMode = Literal["IDLE", "QUANTUM_RESONANCE", "COHERENT", "DECOHERENCE", "MANUAL_OVERRIDE"]

@dataclass
class ResonanceState:
    active: bool
    mode: ResMode
    flow_mult: float
    energy_state: float  # 0.0-1.0
    source: str
    last_event_id: str
    last_updated_ts: float

class ResonanceBus:
    def get_state(self) -> ResonanceState:
        # 1. Try Redis
        # 2. Fall back to neural_stream.log tail
        # 3. Return last known state
```

---

## CONFIG FILES

### human_bias.json

```json
{
    "bias_mode": "AGGRESSIVE",  // AGGRESSIVE | NEUTRAL | CHILL
    "risk_adjustment": 1.2      // Multiplier
}
```

### human_control.json

```json
{
    "kill_switch": false,
    "block_new_entries": false,
    "max_daily_loss_usd": 200.0,
    "max_open_positions": 2
}
```

---

## WORKFLOW: MULTIVERSE → SERAPH → PRODUCTION

```
1. QUANTUM LAB: Train strategy across 10 universe types
   ⚛️ QUANTUM> quick
   
   Output:
   - Best Gene: {regime_cooldown: 420, stop_loss_pct: -2.8, ...}
   - Academy Rank: EXPERT
   - Recommended Changes: [...]

2. QUANTUM LAB: Generate Seraph commands
   ⚛️ QUANTUM> deploy
   
   Output:
   🧠 SERAPH> COOLDOWN_SEC = 300 satırını COOLDOWN_SEC = 420 olarak değiştir
   🧠 SERAPH> MIN_SECONDS_BETWEEN_TRADES = 120 satırını ... = 95 olarak değiştir

3. SERAPH: Execute code modifications
   🧠 SERAPH> COOLDOWN_SEC = 300 satırını COOLDOWN_SEC = 420 olarak değiştir
   
   ✅ Successfully modified regime_detector.py
   💾 Backup: backups/regime_detector_20241209_...
   
   ⚠️ Restart required? (y/n): y

4. PM2: Restart production
   pm2 restart godbrain-quantum
```

---

## CRITICAL PATHS FOR CODE MODIFICATIONS

When modifying these files, ensure:

| File | Critical Variables | Notes |
|------|-------------------|-------|
| `regime_detector.py` | `COOLDOWN_SEC`, `RegimeType` | Must have HOLD state |
| `signal_filter.py` | `MIN_SECONDS_*`, `MAX_*_PER_HOUR` | Call `record_trade()` after exec |
| `agg.py` | Signal filter integration | Wrap execute with filter |
| `human_bias.json` | `bias_mode`, `risk_adjustment` | Valid modes: AGGRESSIVE/NEUTRAL/CHILL |
| `human_control.json` | `kill_switch` | true = stop all trading |

---

## COMMAND REFERENCE

### Seraph Commands

```
status              - Show current config & patches
rollback            - Undo last patch
history             - Show patch history
exit                - Exit

# Natural language:
"agresif moda geç"
"COOLDOWN_SEC = 600 yap"
"yeni trailing stop modülü oluştur"
```

### Quantum Lab Commands

```
quick     - 10 universes, 10 generations
standard  - 10 universes, 30 generations  
deep      - 20 universes, 100 generations
deploy    - Generate Seraph commands
status    - Show DNA Academy leaderboard
exit      - Exit
```

### PM2 Commands

```bash
pm2 list                        # Status
pm2 restart godbrain-quantum    # Restart main
pm2 logs godbrain-quantum       # View logs
```

---

## END OF DOCUMENTATION
