# tests/lib — Reusable Test Components

## Overview

This directory holds shared test infrastructure for the trading strategy test suite.
It is intentionally decoupled from any single test file so it can be imported by
multiple test modules for regression testing.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `fixtures.py` | Shared pytest fixtures + `mock_klines()` data generator |
| `test_momentum_strategy.py` | Self-contained regression tests for `MomentumStrategy` |
| `README.md` | This file |

## Key Design Decisions

### Volume spike alignment

`MomentumStrategy.required_bars = max(rsi_period, volume_ma_period) + 10 = 30`.

The strategy needs **30 bars** before it can emit any signal.  To make the
volume spike (`vol_ratio ≥ 1.5`) visible at that point, `mock_klines()` places
the spike at **bars 35-40** (not 20-25).  This ensures the spike is still inside
the last-20-bar window when the signal window opens at bar 30+.

### RSI in one-directional trends

- **Uptrend (`trend="up"`)**: every bar closes higher → all `deltas > 0` →
  `avg_gain > 0, avg_loss = 0` → RSI = 100 (overbought) ✓
- **Crash (`trend="crash"`)**: every bar closes lower → all `deltas < 0` →
  `avg_gain = 0, avg_loss > 0` → RSI = 0 (oversold) ✓

### Signal logic

| Condition | Action |
|-----------|--------|
| `RSI < rsi_oversold` **AND** `vol_ratio ≥ volume_multiplier` | BUY (if not active) |
| `RSI > rsi_overbought` **AND** `vol_ratio ≥ volume_multiplier` | SELL (if active) |
| Either condition missing | No signal |

## Running Tests

```bash
# Run only the lib regression tests
cd ~/Desktop/special_topic/trading
python3 -m pytest tests/lib/test_momentum_strategy.py -v

# Run all strategy tests (including the original test_strategies.py)
python3 -m pytest tests/ -v
```

## Adding New Strategies

1. Add a `mock_klines(..., trend="new_trend")` branch in `fixtures.py`
2. Create `tests/lib/test_<strategy>.py` using the shared `config` fixture
3. Import `mock_klines` from `tests.lib.fixtures`
