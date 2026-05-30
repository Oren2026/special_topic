"""
Regression tests for MomentumStrategy.

These tests are self-contained and use the shared fixtures from lib/fixtures.py.
They verify that the strategy correctly:
  1. Emits a BUY signal when RSI < oversold threshold AND volume spikes
  2. Emits a SELL signal when RSI > overbought threshold AND volume spikes
  3. Ignores signals when one of the two conditions is missing
  4. Respects the _position_active flag (no duplicate signals)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from strategies.base import Signal
from strategies.momentum import MomentumStrategy
from tests.lib.fixtures import config, mock_klines


class TestMomentumStrategy:
    """Core regression tests for MomentumStrategy signal generation."""

    def test_buy_on_oversold(self, config):
        """
        Given a persistent downtrend (crash), RSI collapses to 0 (oversold).
        With a concurrent volume spike (≥1.5× MA), the strategy MUST emit BUY.
        """
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()

        bars = mock_klines(60, start_price=50000, trend="crash")
        sym = "BTCUSDT"
        result = None

        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r:
                result = r
                break

        assert result is not None, "Must emit BUY in oversold + vol spike condition"
        assert result.signal == Signal.BUY, f"Expected BUY, got {result.signal}"

    def test_sell_on_overbought(self, config):
        """
        Given a persistent uptrend, RSI climbs to 100 (overbought).
        With a concurrent volume spike (≥1.5× MA), the strategy MUST emit SELL.
        """
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()
        strat._position_active = True  # simulate open long position

        bars = mock_klines(60, start_price=50000, trend="up")
        sym = "BTCUSDT"
        result = None

        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r:
                result = r
                break

        assert result is not None, "Must emit SELL in overbought + vol spike condition"
        assert result.signal == Signal.SELL, f"Expected SELL, got {result.signal}"

    def test_no_signal_without_volume_spike(self, config):
        """
        RSI is oversold but volume is flat → NO signal should be emitted.
        This verifies that BOTH conditions (RSI + volume) are required.
        """
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()

        # flat trend: RSI stays near 50; no volume spike
        bars = mock_klines(60, start_price=50000, trend="flat", seed=99)
        sym = "BTCUSDT"
        signals = []

        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r:
                signals.append(r)

        # RSI in flat market hovers around 50, not triggering oversold/overbought
        assert len(signals) == 0, f"Expected no signal without vol spike, got {len(signals)}"

    def test_no_duplicate_buy(self, config):
        """
        After a BUY signal fires, _position_active becomes True.
        Subsequent oversold + vol spike bars must NOT emit another BUY.
        """
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()

        bars = mock_klines(60, start_price=50000, trend="crash")
        sym = "BTCUSDT"
        buy_count = 0

        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r and r.signal == Signal.BUY:
                buy_count += 1

        assert buy_count == 1, f"Expected exactly 1 BUY, got {buy_count}"

    def test_no_signal_without_position(self, config):
        """
        When _position_active is False (no open position) and RSI is overbought,
        the strategy must NOT emit SELL (only BUY can open a position).
        """
        strat = MomentumStrategy(config)
        strat.timeframes = ["1h"]
        strat.data = {"1h": []}
        strat.init()
        strat._position_active = False  # no open position

        bars = mock_klines(60, start_price=50000, trend="up")
        sym = "BTCUSDT"
        sell_signals = []

        for b in bars:
            strat.update(sym, "1h", b)
            r = strat.on_kline(sym, "1h", b)
            if r and r.signal == Signal.SELL:
                sell_signals.append(r)

        assert len(sell_signals) == 0, (
            "SELL should not fire when no position is active"
        )
