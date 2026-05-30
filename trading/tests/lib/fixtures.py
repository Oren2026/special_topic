"""Shared fixtures for strategy tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml
import numpy as np
import pytest


@pytest.fixture(scope="session")
def config():
    """Load strategy config once per session."""
    with open(Path(__file__).parent.parent.parent / "config" / "strategies.yaml") as f:
        return yaml.safe_load(f)


def mock_klines(
    count: int,
    start_price: float = 50000,
    trend: str = "flat",
    volatility: float = 0.005,
    seed: int = 42,
) -> list[dict]:
    """
    Generate synthetic kline data.

    Parameters
    ----------
    count     : total number of bars
    start_price : initial close price
    trend     : 'flat' | 'up' | 'down' | 'crash'
                'up'   → persistent uptrend (RSI → 100)
                'crash'→ persistent downtrend (RSI → 0)
                'down' → moderate downtrend
                'flat' → random walk around start_price
    volatility : fraction of price used as max step (flat only)
    seed      : random seed for reproducibility

    Volume spikes are placed at bars 35-40 to align with the
    required_bars=30 threshold so that signals can fire at bar 30+.
    """
    klines = []
    price = start_price
    np.random.seed(seed)
    base_vol = 100

    for i in range(count):
        if trend == "up":
            # Uptrend: price climbs every bar → RSI=100
            # Volume spike at 35-40 so it survives the required_bars window
            change = price * (0.015 + 0.003 * (i / count))
            vol = 4000 if 35 <= i <= 40 else base_vol

        elif trend == "crash":
            # Crash: price falls every bar → RSI=0
            # Volume spike at 35-40 to align with required_bars window
            change = -price * (0.025 if 15 <= i < 25 else 0.015)
            vol = 3000 if 35 <= i <= 40 else base_vol

        elif trend == "down":
            change = -price * (0.015 + 0.003 * (i / count))
            vol = base_vol + i * 20

        else:
            change = price * volatility * (np.random.random() - 0.5)
            vol = base_vol + i * 20

        price += change
        klines.append({
            "timestamp": 1700000000 + i * 300,
            "open":  price - change,
            "high":  price + abs(change) * 0.2,
            "low":   price - abs(change) * 0.2,
            "close": price,
            "volume": vol,
        })

    return klines
