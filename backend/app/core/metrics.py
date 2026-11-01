"""Accuracy metrics computed on aligned (actual, forecast) pairs, no ML involved."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from app.core.config import NORMALISATION_FLOOR_MW
from app.core.decision import horizon_bucket


@dataclass
class MetricSummary:
    n: int
    bias: float  # mean error (forecast - actual), MW
    mae: float   # mean absolute error, MW
    rmse: float  # root mean squared error, MW
    p50_abs: float  # median absolute error, MW
    p90_abs: float  # 90th percentile absolute error, MW
    p95_abs: float  # 95th percentile absolute error, MW
    mape: float | None   # mean absolute % error (only where actual >= floor), %
    norm_mae: float | None  # mean abs error / mean actual above floor, fraction

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "bias": round(self.bias, 1),
            "mae": round(self.mae, 1),
            "rmse": round(self.rmse, 1),
            "p50Abs": round(self.p50_abs, 1),
            "p90Abs": round(self.p90_abs, 1),
            "p95Abs": round(self.p95_abs, 1),
            "mapePct": None if self.mape is None else round(self.mape, 1),
            "normMae": None if self.norm_mae is None else round(self.norm_mae, 3),
        }


def percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile on pre-sorted values (q in [0, 100])."""
    if not sorted_values:
        raise ValueError("percentile of empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * q / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def summary_metrics(errors_mw: list[float], actuals_mw: list[float]) -> MetricSummary:
    """Aggregate metrics for a set of aligned pairs.

    errors_mw must equal forecast - actual for each pair. MAPE and normalised
    MAE are computed only on pairs whose actual >= NORMALISATION_FLOOR_MW.
    """
    if not errors_mw:
        raise ValueError("summary_metrics called with no pairs")
    abs_err = sorted(abs(e) for e in errors_mw)
    bias = sum(errors_mw) / len(errors_mw)
    mae = sum(abs_err) / len(abs_err)
    rmse = sqrt(sum(e * e for e in errors_mw) / len(errors_mw))

    qualified = [
        (a, e) for a, e in zip(actuals_mw, errors_mw)
        if a >= NORMALISATION_FLOOR_MW
    ]
    mape: float | None = None
    norm_mae: float | None = None
    if qualified:
        mape = 100.0 * sum(abs(e) / a for a, e in qualified) / len(qualified)
        mean_actual = sum(a for a, _ in qualified) / len(qualified)
        norm_mae = mae / mean_actual if mean_actual > 0 else None

    return MetricSummary(
        n=len(errors_mw),
        bias=bias,
        mae=mae,
        rmse=rmse,
        p50_abs=percentile(abs_err, 50),
        p90_abs=percentile(abs_err, 90),
        p95_abs=percentile(abs_err, 95),
        mape=mape,
        norm_mae=norm_mae,
    )


def error_distribution(errors_mw: list[float], bins_mw: list[float]) -> dict:
    """Histogram of errors (MW) on given bin edges (len B -> B-1 buckets)."""
    counts = [0] * (len(bins_mw) - 1)
    for e in errors_mw:
        e = min(max(e, bins_mw[0]), bins_mw[-1])
        i = 0
        while i < len(counts) - 1 and e >= bins_mw[i + 1]:
            i += 1
        counts[i] += 1
    return {
        "edges": bins_mw,
        "counts": counts,
        "labels": [
            f"{bins_mw[i]:+,.0f}" for i in range(len(bins_mw) - 1)
        ],
    }


def error_percentiles(errors_mw: list[float]) -> dict:
    """Empirical percentiles of signed error used for uncertainty bands."""
    s = sorted(errors_mw)
    return {
        "p10": percentile(s, 10),
        "p25": percentile(s, 25),
        "p50": percentile(s, 50),
        "p75": percentile(s, 75),
        "p90": percentile(s, 90),
    }
