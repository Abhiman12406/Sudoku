# IO Signal Sudoku: DeltaV Electronic Marshalling Automated Allocation & Revision Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=Abhiman12406/Sudoku&branch=main&mainModule=streamlit_app.py)

An industrial-grade constraint-programming allocation engine and web application for **Emerson DeltaV Electronic Marshalling (CHARMs)** systems. Formulated mathematically as a multi-dimensional Sudoku constraint satisfaction problem using **Google OR-Tools CP-SAT**.

---

## 🌟 Key Capabilities

1. **Two-Stage Hierarchical Packing**
   - **Macro-Packer**: Knapsack-style CIOC/Baseplate packing respecting cable contiguity and spare quotas.
   - **Micro-Slotter**: Exact physical slot assignment (1–12) within baseplates in strictly ascending pair order.

2. **Safety-Critical A/B Segregation**
   - Enforces physical separation of Train A and Train B redundant signals to disjoint CIOCs using linearized $U_c^A + U_c^B \le 1$ indicators.

3. **Revision Diff & Perturbation Minimization (Rev A vs Rev B)**
   - Minimal disruption engine: freezes physically wired signals, classifies delta (Identical, Reparameterized, Moved, Added, Deleted), and penalizes physical rework with weighted perturbation penalties.

4. **Automated Technical Query (TQ) Engine**
   - Flags corrupt, missing, or contradictory instrument tags with formal TQ engineering clarification documents (`TQ-INST-xxx`).

5. **Industrial Excel & Audit Deliverables**
   - Professional multi-sheet engineering deliverable with color-coded signal schedules, revision diff audit tables, and TQ records preserving original customer styling.

6. **Interactive Streamlit Web UI & Cabinet Visualizer**
   - Interactive DIN-rail cabinet visualizer, live hardware catalog editor, 10,000-signal scalability stress benchmark, and one-click deliverable exports.

---

## 🚀 Cloud Deployment (Streamlit Community Cloud)

You can deploy this application directly to [Streamlit Community Cloud](https://share.streamlit.io/):

1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
2. Click **New app**.
3. Select this repository: `Abhiman12406/Sudoku`.
4. Branch: `main`.
5. Main file path: `streamlit_app.py` (or `src/ui/app.py`).
6. Click **Deploy!**

Alternatively, click the **Deploy to Streamlit** badge above for a pre-filled deployment page.

---

## 💻 Local Development Setup

### Prerequisites
- Python 3.10+ (Recommended Python 3.11 or 3.12)
- Git

### Installation
```bash
git clone https://github.com/Abhiman12406/Sudoku.git
cd Sudoku

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Web Application
```bash
streamlit run streamlit_app.py
```
Or directly:
```bash
streamlit run src/ui/app.py
```
Open your browser at `http://localhost:8501`.

### Running Tests & Benchmarks
```bash
# Run full test suite
pytest

# Run UI tests
pytest tests/test_ui.py

# Run 10k signal stress benchmark
python scripts/run_10k_benchmark.py --signals 10000 --threads 8
```

---

## 📁 Project Architecture

```
├── streamlit_app.py         # Streamlit Community Cloud root entrypoint
├── requirements.txt         # Production dependencies
├── CONTEXT.md               # Domain model and ubiquitous language
├── src/
│   ├── domain/              # CHARM hardware catalog, signal, cable models
│   ├── ingestion/           # Excel parser, validation, TQ generator
│   ├── solver/              # Two-stage hierarchical CP-SAT solver
│   ├── revision/            # Rev A vs Rev B perturbation minimization engine
│   ├── export/              # Excel deliverable exporter & audit reporter
│   ├── benchmark/           # 10k scalability synthetic generator & telemetry
│   └── ui/                  # Streamlit web app & cabinet visualizer
├── tests/                   # Pytest test suite (>68 comprehensive tests)
└── docs/                    # Architecture Decision Records & design specs
```
