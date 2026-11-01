import pytest

from app.core.metrics import error_distribution, error_percentiles, percentile, summary_metrics


def test_percentile_interpolation():
    vals = sorted([1, 2, 3, 4])
    assert percentile(vals, 0) == 1
    assert percentile(vals, 100) == 4
    assert percentile(vals, 50) == 2.5
    assert percentile(vals, 25) == 1.75


def test_summary_metrics_basic():
    errors = [-100.0, 50.0, 100.0]
    actuals = [2000.0, 2000.0, 2000.0]
    ms = summary_metrics(errors, actuals)
    assert ms.n == 3
    assert ms.bias == pytest.approx(50 / 3)
    assert ms.mae == pytest.approx(250 / 3)
    assert ms.rmse == pytest.approx(((10000 + 2500 + 10000) / 3) ** 0.5)
    assert ms.p50_abs == pytest.approx(100.0)
    # all actuals above floor -> mape defined
    assert ms.mape is not None
    assert ms.mape == pytest.approx(100 * ((100 / 2000) + (50 / 2000) + (100 / 2000)) / 3)


def test_summary_metrics_mape_guard_for_near_zero_actuals():
    errors = [500.0, 10.0]
    actuals = [300.0, 20.0]  # both below NORMALISATION_FLOOR_MW=1000
    ms = summary_metrics(errors, actuals)
    assert ms.mape is None
    assert ms.norm_mae is None


def test_summary_metrics_empty_raises():
    with pytest.raises(ValueError):
        summary_metrics([], [])


def test_error_distribution_bins():
    hist = error_distribution([-1500.0, 100.0, 700.0], [-1000, 0, 500, 1000])
    # bins: [-1000,0), [0,500), [500,1000]; clamped -1500 goes to first bin
    assert hist["counts"] == [1, 1, 1]


def test_error_percentiles_sorted_signage():
    pct = error_percentiles([-9, -5, -1, 3, 7, 11, 15, 19, 23, 27])
    assert pct["p10"] < pct["p50"] < pct["p90"]
    assert pct["p50"] == 9.0  # interpolates (7+11)/2
