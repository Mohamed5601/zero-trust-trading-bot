# Quant-Intel: Event-Driven Crypto Market Analysis

A modular, event-driven crypto market analysis pipeline built for selective computation and multi-layer signal generation.

Quant-Intel is a research system designed to reduce unnecessary computation in market analysis by only activating heavy logic when abnormal market behavior is detected. The system combines rule-based heuristics, statistical indicators, and machine learning models in a staged pipeline.

## Overview

Most trading systems either:
* Run heavy analysis continuously on all assets (expensive and noisy), or
* Rely on overly simplified signal logic.

Quant-Intel sits in between. It introduces a two-stage architecture:
1. Lightweight market scanning
2. Targeted multi-agent analysis on selected assets

The goal is not to predict the market perfectly, but to structure analysis in a way that is efficient, modular, and testable.

---

## Architecture

### 1. Market Scout Layer
This layer runs continuously and is responsible for filtering the market.

**Components:**
* `get_top_volume_coins.py`: Tracks relative volume changes across assets and identifies anomalies.
* `whale_radar.py`: Monitors order flow patterns to approximate buy/sell pressure.

**Output:**
A filtered list of assets that show unusual activity or structural changes in flow. The scout layer is intentionally lightweight and prioritizes coverage over depth.

### 2. Analysis Layer
Once an asset passes the scout filter, it is passed into a set of independent analysis modules. Each module focuses on a specific aspect of market behavior:

* **`general_bot.py`**
  Evaluates overall trend direction and market structure.
* **`volume_bot.py`**
  Analyzes volume expansion and confirms momentum consistency.
* **`sniper_bot.py`**
  Attempts to identify potential entry zones based on short-term volatility patterns.
* **`risk_bot.py`**
  Calculates dynamic risk parameters (stop-loss / take-profit) using volatility measures such as ATR.
* **`ai_agent.py`**
  Machine learning model (XGBoost) trained on engineered features to estimate short-term directional bias.
* **`market_analyst.py`**
  Aggregates outputs into a readable summary of market conditions for interpretation.

---

## Design Principles

* **Event-driven execution**
  The system does not run full analysis continuously. Computation is triggered only when market conditions justify it.

* **Modular separation**
  Each analytical component is independent. This allows:
  * Easier testing
  * Isolated improvements
  * Replacement of individual strategies without breaking the pipeline

* **Hybrid reasoning**
  The system does not rely on a single approach:
  * Rule-based logic for structure
  * Statistical indicators for confirmation
  * ML model for probabilistic bias

---

## Tech Stack

* **Core:** Python 3.x
* **Data & Math:** `pandas` / `numpy` / `pandas-ta`
* **Intelligence:** `XGBoost`
* **Infrastructure:** `ccxt` (exchange data integration) / `cloudscraper` (data acquisition layer)
* **Alerting:** Telegram Bot API

---

## Output Flow

1. Market scanner detects abnormal volume activity.
2. Whale radar validates flow imbalance.
3. Asset is passed to analysis pipeline.
4. Each module produces independent signals.
5. Signals are aggregated into a final structured report.
6. Optional alert is sent via Telegram.

---

## Limitations

This system is experimental and should not be considered production-grade. Current limitations include:
* Sensitivity to market regime changes.
* Dependency on data quality from external sources.
* Signal aggregation is still heuristic-based.
* ML model requires continuous retraining for stability.

---

## Status & Notes

**Active research prototype.**
The focus is on architecture design and signal structuring rather than guaranteed predictive performance.

*Note:* The system is intentionally designed to be inspectable. Every decision path can be traced back to a specific module rather than a single opaque model.
