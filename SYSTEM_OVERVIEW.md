# GODBRAIN QUANTUM - System Overview

## What is GODBRAIN?
An autonomous AI-powered quantitative trading system that evolves trading strategies using genetic algorithms, quantum computing, and multi-LLM orchestration.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GODBRAIN.ORG (Cloudflare)                    │
│         godbrain.org │ app.godbrain.org │ api.godbrain.org      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Cloudflare Tunnel
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Host (Windows)                       │
├────────────────┬────────────────┬────────────────┬──────────────┤
│  Mobile App    │  Mobile API    │   Dashboard    │    Redis     │
│  (Next.js)     │  (Flask:8001)  │  (Flask:8000)  │  (:16379)    │
│  :3000         │                │  + Seraph AI   │              │
└────────────────┴────────────────┴────────────────┴──────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Core Trading Services                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   VOLTRAN       │   Market Feed   │     Genetics Lab            │
│   (agg.py)      │   (OKX WSS)     │  Blackjack/Roulette/Chaos   │
│   Aggregator    │   BTC/USDT      │     DNA Evolution           │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Intelligence Layer                            │
├────────────────┬────────────────┬────────────────┬──────────────┤
│ Quantum Lab    │ Quantum Genesis│ Anomaly Hunter │  Sentinel    │
│ (DNA Wisdom)   │ (IBM Quantum)  │ (Detection)    │ (Self-Heal)  │
└────────────────┴────────────────┴────────────────┴──────────────┘
```

---

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **Backend** | Python 3.11, Flask, Redis |
| **Frontend** | Next.js 16, React 19, TypeScript, TailwindCSS |
| **AI/ML** | Claude 3.5, GPT-4, Gemini 2.0, Multi-LLM Router |
| **Quantum** | IBM Quantum (Qiskit), QAOA circuits |
| **Data** | OKX WebSocket, Real-time BTC/USDT |
| **Infrastructure** | Docker Compose, Cloudflare Tunnel |
| **Evolution** | Genetic Algorithms, DNA-based strategies |

---

## Docker Services (12 Total)

| Service | Purpose | Port |
|---------|---------|------|
| `godbrain-redis` | Central data store | 16379 |
| `godbrain-market-feed` | OKX price feed | - |
| `godbrain-voltran` | Trading aggregator | - |
| `godbrain-dashboard` | Web UI + Seraph AI | 8000 |
| `godbrain-genetics` | Lab simulations | - |
| `godbrain-quantum-lab` | DNA evolution | - |
| `godbrain-quantum-genesis` | IBM Quantum integration | - |
| `godbrain-anomaly-hunter` | Anomaly detection | - |
| `godbrain-sentinel` | Self-healing monitor | - |
| `godbrain-feedback-loop` | Backtesting | - |
| `godbrain-dna-pusher` | Strategy injection | - |
| `godbrain-mobile-api` | Mobile REST API | 8001 |

---

## Key Modules

### 1. VOLTRAN (`core/agg.py`)
Main trading aggregator. Collects signals from all labs, calculates consensus, manages risk.

### 2. Seraph AI (`seraph/`)
Multi-LLM AI assistant with:
- **LLM Router**: Routes queries to best model (Claude/GPT/Gemini)
- **Quantum Wisdom**: Injects DNA discoveries into responses
- **Long-term Memory**: Stores conversation context

### 3. Quantum Lab (`quantum_lab/`)
DNA strategy evolution:
- Evolves trading parameters over generations
- Produces "wisdom" from successful strategies
- Current: Generation 5660+

### 4. Quantum Genesis (`quantum_genesis/`)
IBM Quantum integration:
- Runs QAOA circuits for optimization
- Generates quantum anomalies
- Connected to IBM Brisbane quantum computer

### 5. Anomaly Hunter (`anomaly_hunter/`)
Detects market anomalies using:
- Statistical methods
- Z-score analysis
- Pattern recognition

### 6. Genetics Labs (`core/genetics_lab.py`)
Three simulation labs:
- **Blackjack**: Card counting strategies
- **Roulette**: Probability analysis
- **Chaos**: Randomness exploitation

---

## Last 3 Days Development (Dec 18-20, 2025)

### Day 1: Multi-LLM Architecture
- Implemented LLM Router for Claude/GPT/Gemini
- Added provider failover
- Integrated into Seraph AI

### Day 2: Mobile App Integration
- Created mobile_api.py REST API
- Updated Next.js components for real data
- Fixed hydration errors
- Connected to Redis for live metrics

### Day 3: Domain & Permanent Deployment
- Purchased godbrain.org domain
- Set up Cloudflare Tunnel (named tunnel)
- Dockerized mobile API
- Created startup scripts
- Git pushed all changes

---

## Live Endpoints

| URL | Returns |
|-----|---------|
| `https://godbrain.org` | Mobile App UI |
| `https://api.godbrain.org/api/status` | System metrics (voltran, DNA gen) |
| `https://api.godbrain.org/api/market` | BTC price from Redis |
| `https://api.godbrain.org/api/seraph/chat` | AI chat endpoint |
| `https://api.godbrain.org/api/llm-status` | LLM provider status |

---

## Key Files

```
godbrain-quantum/
├── mobile_api.py          # REST API for mobile
├── core/agg.py            # VOLTRAN aggregator
├── seraph/
│   ├── seraph.py          # AI assistant
│   └── llm_router.py      # Multi-LLM routing
├── quantum_lab/           # DNA evolution
├── quantum_genesis/       # IBM Quantum
├── anomaly_hunter/        # Anomaly detection
├── mobile-app/            # Next.js frontend
│   ├── lib/api.ts         # API client
│   └── components/        # React components
└── docker-compose.yml     # All services
```

---

## Current State (Dec 20, 2025)
- **DNA Generation**: 5660+
- **VOLTRAN Score**: 85.0
- **Docker Services**: 12 running
- **Uptime**: 47+ hours
- **Domain**: godbrain.org (Cloudflare)

---

## Quick Start for New LLMs

1. **Redis is the brain** - All data flows through Redis
2. **VOLTRAN is the heart** - Aggregates all signals
3. **DNA evolves** - Strategies improve over generations
4. **Seraph speaks** - AI explains everything
5. **Quantum enhances** - IBM Quantum for optimization

**Key command to check status:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
