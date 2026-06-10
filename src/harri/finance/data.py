# --------------------------------------------------------------------------------------
# IMPORTS AND CONSTANTS
# --------------------------------------------------------------------------------------
# Standard Library Imports
from dataclasses import dataclass, field

# Third-Party Imports
import numpy as np
import pandas as pd
from scipy import stats

# --------------------------------------------------------------------------------------
# DATA STRUCTURE
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Asset:
    name: str
    ticker: str
    totrets: np.ndarray = field(repr=False)
    closes: np.ndarray = field(repr=False)
    freq: int = 252
    dates: pd.DatetimeIndex | None = field(default=None, repr=False)

    # Calculated
    _ret_facts: np.ndarray = field(init=False, repr=False)
    adj_close: np.ndarray = field(init=False, repr=False)
    cumul_rets: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        ret_facts = (self.totrets / 100) + 1

        # Assign values using the frozen setter bypass
        object.__setattr__(self, "_ret_facts", ret_facts)
        object.__setattr__(self, "adj_close", self._compute_adj_close())
        object.__setattr__(self, "cumul_rets", np.cumprod(ret_facts))

        # Make arrays immutable
        for arr in [
            self.totrets,
            self.closes,
            self._ret_facts,
            self.adj_close,
            self.cumul_rets,
        ]:
            arr.flags.writeable = False

    def __repr__(self) -> str:
        # Pull the number of observations from one of your arrays
        obs_count = len(self.totrets) if self.totrets is not None else 0

        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"ticker={self.ticker!r}, "
            f"freq={self.freq}, "
            f"obs_count={obs_count})"
        )

    # ── private helpers ────────────────────────────────────────────
    def _ret_factors(self) -> np.ndarray:
        return self._ret_facts

    def _geomean(self) -> float:
        return np.prod(self._ret_facts) ** (1 / len(self.totrets)) - 1

    def _arithmetic_mean(self) -> float:
        return float(np.mean(self.totrets) / 100)

    def _compute_adj_close(self) -> np.ndarray:
        # Anchor to last close, backfill using ret factors
        factors = self._ret_facts[::-1]
        prices = np.empty(len(factors) + 1)
        prices[0] = self.closes[-1]
        for i, f in enumerate(factors):
            prices[i + 1] = prices[i] / f
        return prices[-2::-1]

    def _cumul_rets(self) -> np.ndarray:
        """Cumulative return factors over time, starting at 1."""
        return np.cumprod(self._ret_facts)

    # ── public metrics (percentages unless noted) ──────────────────
    def TR(self) -> float:
        return float(self.cumul_rets[-1] - 1) * 100

    def CAGR(self) -> float:
        return ((self._geomean() + 1) ** self.freq - 1) * 100

    def vol(self) -> float:
        return np.std(self.totrets, ddof=1) * np.sqrt(self.freq)

    def sharpe(self, rf: float = 0.0) -> float:
        ann_mean = self._arithmetic_mean() * self.freq * 100  # %
        return (ann_mean - rf) / self.vol()

    def max_drawdown(self) -> float:
        peak = np.maximum.accumulate(self.adj_close)
        dd = (self.adj_close - peak) / peak
        return float(np.min(dd) * 100)

    def calmar(self) -> float:
        mdd = self.max_drawdown()
        return self.CAGR() / abs(mdd) if mdd != 0 else np.nan

    def skew(self) -> float:
        return float(stats.skew(self.totrets))

    def kurtosis(self) -> float:
        return float(stats.kurtosis(self.totrets))  # Fisher (excess)

    def win_rate(self) -> float:
        return float(np.sum(self.totrets > 0) / len(self.totrets) * 100)

    def n_periods(self) -> int:
        return len(self.totrets)

    def summary(self) -> dict:
        """
        Returns a dict of annualized performance metrics for the asset.

        All percentage fields (suffixed _%) are in percent terms (e.g. 5.0 = 5%).
        Ratios (sharpe, calmar) and distribution stats (skew, kurtosis) are
        dimensionless.

        Keys:
            TR_%        Total return over the full period.
            CAGR_%      Compound annual growth rate (geometric).
            vol_%       Annualized volatility (std of periodic returns × √freq).
            sharpe      Annualized Sharpe ratio vs rf=0 (arithmetic mean / vol).
            max_dd_%    Maximum peak-to-trough drawdown on adj_close.
            calmar      CAGR / |max_drawdown|.
            skew        Return distribution skewness (bias=True).
            kurtosis    Excess kurtosis, Fisher convention (normal → 0).
            win_rate_%  Proportion of periods with positive return.
            freq        Periods per year used for annualization.
            n           Number of observations.
        """
        return {
            "TR_%": round(self.TR(), 4),
            "CAGR_%": round(self.CAGR(), 4),
            "vol_%": round(self.vol(), 4),
            "sharpe": round(self.sharpe(), 4),
            "max_dd_%": round(self.max_drawdown(), 4),
            "calmar": round(self.calmar(), 4),
            "skew": round(self.skew(), 4),
            "kurtosis": round(self.kurtosis(), 4),
            "win_rate_%": round(self.win_rate(), 4),
            "freq": self.freq,
            "n": self.n_periods(),
        }
