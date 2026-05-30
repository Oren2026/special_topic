import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import numpy as np
import pytest

from strategies.base import Signal
from strategies.grid import GridStrategy
from strategies.momentum import MomentumStrategy
from strategies.trend_follow import TrendFollowStrategy


@pytest.fixture(scope="module")
def config():
    with open("config/strategies.yaml") as f:
        return yaml.safe_load(f)


def _mock_klines(count: int, start_price: float = 50000,
                 trend: str = "flat", volatility: float = 0.005,
                 seed: int = 42) -> list[dict]:
    klines = []
    price = start_price
    np.random.seed(seed)
    base_vol = 100   # keep low so vol_ratio crosses 1.5x threshold for "up" test
    for i in range(count):
        if trend == "up":
            # persistent uptrend → RSI stays overbought at 100
            # spike vol at bar 35-40 so it survives the required_bars=30 window
            change = price * (0.015 + 0.003 * (i / count))
            vol = 4000 if 35 <= i <= 40 else base_vol
        elif trend == "down":
            change = -price * (0.015 + 0.003 * (i / count))
            vol = base_vol + i * 20
        elif trend == "crash":
            # persistent downtrend → RSI collapses to oversold
            # spike vol at bar 35-40 to align with required_bars=30 window
            change = -price * (0.025 if i in range(15, 25) else 0.015)
            vol = 3000 if 35 <= i <= 40 else base_vol
        else:
            change = price * 0.001 * (np.random.random() - 0.5)
            vol = base_vol + i * 20
        price += change
        klines.append({
            "timestamp": 1700000000 + i * 300,
            "open": price - change,
            "high": price + abs(change) * 0.2,
            "low": price - abs(change) * 0.2,
            "close": price,
            "volume": vol,
        })
    return klines


class TestMomentumStrategy:
    def test_buy_on_oversold(self, config):
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()
        bars = _mock_klines(60, start_price=50000, trend="crash")
        sym = "BTCUSDT"
        result = None
        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r:
                result = r
                break
        assert result is not None, "應該在超賣區產生買入訊號"
        assert result.signal == Signal.BUY

    def test_sell_on_overbought(self, config):
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()
        strat._position_active = True
        bars = _mock_klines(60, start_price=50000, trend="up")
        sym = "BTCUSDT"
        result = None
        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r:
                result = r
                break
        assert result is not None, "應該在超買區產生賣出訊號"
        assert result.signal == Signal.SELL


class TestTrendFollowStrategy:
    def test_buy_on_golden_cross(self, config):
        strat = TrendFollowStrategy(config)
        strat.timeframes = ["1d"]
        strat.data = {"1d": []}
        strat.init()
        bars = _mock_klines(60, start_price=50000, trend="flat")
        last = bars[-1]["close"]
        bars += _mock_klines(80, start_price=last, trend="up")
        sym = "BTCUSDT"
        result = None
        for b in bars:
            strat.update(sym, "1d", b)
            r = strat.on_kline(sym, "1d", b)
            if r:
                result = r
                break
        assert result is not None, "EMA 黃金交叉應產生買入訊號"
        assert result.signal == Signal.BUY


class TestGridStrategy:
    def test_grid_places_orders(self, config):
        strat = GridStrategy(config)
        strat.timeframes = ["5m"]
        strat.data = {"5m": []}
        strat.init()
        bars = _mock_klines(100, start_price=50000, trend="up", volatility=0.008)
        sym = "BTCUSDT"
        signals = []
        for b in bars:
            strat.update(sym, "5m", b)
            r = strat.on_kline(sym, "5m", b)
            if r:
                signals.append(r)
        assert len(signals) > 0, f"網格策略應在波動中產生訊號 (got {len(signals)})"
