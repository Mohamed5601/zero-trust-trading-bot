# Quant-Intel

Quant-Intel is a modular, event-driven system built to analyze crypto markets without burning unnecessary CPU cycles. Instead of running heavy calculations on every asset 24/7, it filters the market first and only triggers deep analysis when it detects unusual activity.

## Why I built it this way

Most trading setups either run heavy analysis continuously on everything (which is slow, expensive, and noisy) or rely on simple rules that completely miss the market context. 

This setup sits in the middle: a lightweight scout layer monitors the market in the background, and a more detailed multi-bot analysis pipeline kicks in only when a real trigger occurs. The goal was to build a system that is efficient, modular, and easy to debug.

## Architecture

### 1. Scout & Real-Time Monitoring Layer
This layer runs continuously and filters the market in real time. Its main job is to detect unusual movement early without running heavy analysis on every asset. 
If you're experimenting with short-term or fast scalping setups, this is the part responsible for feeding the system with low-latency market data.

* **`radar.py`**: Streams live price and open interest updates through WebSockets with minimal delay. Mainly used for monitoring fast momentum changes and short-term volatility.
* **`get_top_volume_coins.py`**: Tracks relative volume expansion across assets and flags abnormal spikes.
* **`whale_radar.py`**: Watches order flow activity to estimate larger buying and selling pressure. (Older REST-based implementation kept for compatibility/testing.)

* **Output:** A filtered list of assets showing unusual activity or momentum changes.

### 2. Analysis & Execution Layer
Once an asset is flagged by the scout layer, it is passed into a group of independent modules for deeper evaluation and trade management.

* **`ZK.py`**: Experimental scalping module designed to work alongside the live stream from radar.py. Focuses on fast reaction and short-duration trade tracking.
* **`general_bot.py`**: Evaluates overall trend direction and market structure.
* **`volume_bot.py`**: Confirms whether momentum is supported by volume expansion.
* **`sniper_bot.py`**: Searches for short-term entry zones based on volatility behavior.
* **`risk_bot.py`**: Calculates dynamic Stop-Loss and Take-Profit levels using ATR-based volatility measurements.
* **`ai_agent.py`**: XGBoost classifier trained on engineered market features to estimate short-term directional bias.
* **`market_analyst.py`**: Uses the Gemini API to convert raw technical outputs into a readable market summary.

### 3. Data & Model Layer
This layer separates stored models and historical datasets from the live execution logic.

* **`/models`**: Contains pre-trained .pkl models for assets such as BTC, ETH, XRP, ADA, and DOGE.
* **`/data`**: Historical .csv datasets collected during 2025 and used for training, testing, and parameter tuning.
---

## Design Choices

* **Event-Driven Execution:** Heavy analysis scripts stay idle until a volume or order flow trigger happens. No wasted compute.
* **Strict Modularity:** Every module operates in isolation. You can rewrite, tweak, or replace any bot without breaking the rest of the pipeline.
* **Hybrid Logic:** The system doesn't rely on just one tool. It combines structural rules, statistical indicators, and machine learning probability.

---

## Tech Stack

* Python 3.x
* pandas, numpy, pandas-ta
* XGBoost
* ccxt & cloudscraper
* Telegram Bot API

---

## The Flow

1. Market scanner detects a sudden volume spike.
2. Whale radar checks if big players are backing the move.
3. The selected asset is routed into the analysis pipeline.
4. Each module processes the data and generates its own signal.
5. Results are aggregated into a single report and sent via Telegram.

---

## Project Status: Completed Build (Archived Late 2025)

This is a finished, feature-complete research project. Active development successfully concluded at the end of 2025, and the codebase is locked as a stable reference design.

* **Note on Maintenance (2026+):** Because exchange APIs (CCXT/Binance) and LLM endpoints (Gemini) change frequently, running this codebase today will require routine dependency updates and minor refactoring to fix payload structures and broken package specs.

---

## Guidelines & Disclaimer

* **Test with fake money first:** If you intend to use this framework for personal trading, run it in a paper-trading environment first. Default parameters are just examples; you are fully responsible for tuning configurations to match your own risk tolerance.
* **Legal Disclaimer:** This software is provided "as is" for research and educational purposes. The author assumes no responsibility or legal liability for financial losses, bugs, or misuse of this code. Live deployment is strictly at your own risk.
* **No Black Boxes:** The entire system is completely transparent. Every single alert can be audited and traced back to the exact code module that triggered it.

---

## Contact

If you have any questions, need help setting up the system, or want to discuss the architecture, feel free to reach out via email at: **bvize.com@gmail.com**
