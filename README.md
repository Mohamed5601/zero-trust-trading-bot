# Quant-Intel

Quant-Intel is a modular, event-driven system built to analyze crypto markets without burning unnecessary CPU cycles. Instead of running heavy calculations on every asset 24/7, it filters the market first and only triggers deep analysis when it detects unusual activity.

## Why I built it this way

Most trading setups either run heavy analysis continuously on everything (which is slow, expensive, and noisy) or rely on simple rules that completely miss the market context. 

This setup sits in the middle: a lightweight scout layer monitors the market in the background, and a more detailed multi-bot analysis pipeline kicks in only when a real trigger occurs. The goal was to build a system that is efficient, modular, and easy to debug.

## Architecture

### 1. Market Scout Layer (Continuous Filtering)
This layer runs constantly to monitor the market and filter out the noise.
* `get_top_volume_coins.py`: A lightweight scanner that tracks relative volume changes and flags unusual spikes.
* `whale_radar.py`: Monitors real-time order flows to estimate large buying and selling pressure.

**Output:** A filtered shortlist of assets showing abnormal activity, ready for deep inspection.

### 2. Analysis Layer (Triggered on Demand)
Once the scout layer flags a specific coin, it automatically hands it over to these independent modules:
* `general_bot.py`: Evaluates the macro trend direction and basic market structure.
* `volume_bot.py`: Checks volume expansion to confirm if the momentum is real.
* `sniper_bot.py`: Looks for short-term entry zones based on volatility patterns.
* `risk_bot.py`: Dynamically calculates Stop-Loss and Take-Profit levels using ATR volatility.
* `ai_agent.py`: An XGBoost classifier that estimates short-term directional bias using engineered features.
* `market_analyst.py`: Connects to the Gemini API to turn raw technical metrics into a readable text summary.

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
