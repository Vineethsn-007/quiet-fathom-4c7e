from datetime import date, datetime, time, timezone

from app.core.decision import (
    cutoff_utc_for_delivery,
    horizon_bucket,
    horizon_hours,
    london_date_to_utc,
    select_latest_forecast,
)


def test_cutoff_gmt_winter_is_same_instant_as_utc():
    # January is GMT: 09:00 London == 09:00 UTC
    got = cutoff_utc_for_delivery(date(2026, 1, 15), time(9, 0))
    assert got == datetime(2026, 1, 14, 9, 0, tzinfo=timezone.utc)


def test_cutoff_after_dst_change():
    # BST starts 2026-03-29: 09:00 London == 08:00 UTC from Mar 29 onward
    before = cutoff_utc_for_delivery(date(2026, 3, 29), time(9, 0))
    assert before == datetime(2026, 3, 28, 9, 0, tzinfo=timezone.utc)  # cutoff Mar 28 (GMT)
    after = cutoff_utc_for_delivery(date(2026, 3, 30), time(9, 0))
    assert after == datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc)  # cutoff Mar 29 (BST)
    assert after == before + timedelta_24h() + ( -1 * plus_1h())


def london_date_to_utc_nonexistent_time_raises_or_normalises():
    # 2026-03-29 01:30 London does not exist (spring forward at 01:00).
    got = london_date_to_utc(date(2026, 3, 29), time(1, 30))
    # zoneinfo maps it to UTC+1:30 via gap rules; assert it is a sane UTC instant
    assert got.tzinfo is not None
    assert got in (datetime(2026, 3, 29, 1, 30, tzinfo=timezone.utc), datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc))


def test_select_latest_forecast_picks_greatest_publish_le_cutoff(sample_forecasts):
    cutoff = datetime(2026, 1, 14, 8, 0, tzinfo=timezone.utc)
    rows = select_latest_forecast(sample_forecasts, cutoff, start_from=datetime(2026, 1, 15, 0, tzinfo=timezone.utc), start_to=datetime(2026, 1, 16, 0, tzinfo=timezone.utc))
    assert len(rows) == 2
    jan15h0 = next(r for r in rows if r["startTime"] == datetime(2026, 1, 15, 0, tzinfo=timezone.utc))
    assert jan15h0["publishTime"] == datetime(2026, 1, 14, 2, 30, tzinfo=timezone.utc)
    assert jan15h0["generation"] == 5000.0
    assert jan15h0["horizonHours"] == horizon_hours(jan15h0["startTime"], jan15h0["publishTime"]) == 21.5


def test_select_latest_forecast_cutoff_inclusive(sample_forecasts):
    # publish at exactly the cutoff is included (<=)
    cutoff = datetime(2026, 1, 14, 9, 0, tzinfo=timezone.utc)
    rows = select_latest_forecast(sample_forecasts, cutoff, start_from=datetime(2026, 1, 15, 0, tzinfo=timezone.utc), start_to=datetime(2026, 1, 16, 0, tzinfo=timezone.utc))
    jan15h0 = next(r for r in rows if r["startTime"] == datetime(2026, 1, 15, 0, tzinfo=timezone.utc))
    assert jan15h0["generation"] == 6500.0


def test_next_day_start_excluded(sample_forecasts):
    start_from = datetime(2026, 1, 15, 0, tzinfo=timezone.utc)
    start_to = datetime(2026, 1, 16, 0, tzinfo=timezone.utc)
    rows = select_latest_forecast(sample_forecasts, start_to, start_from, start_to)
    assert all(
        datetime(2026, 1, 15, 0, tzinfo=timezone.utc) <= r["startTime"] < start_to for r in rows
    )


def test_horizon_bucket_edges():
    assert horizon_bucket(0) == "0-6h"
    assert horizon_bucket(5.99) == "0-6h"
    assert horizon_bucket(6) == "6-12h"
    assert horizon_bucket(13.5) == "12-18h"
    assert horizon_bucket(24) == "24-36h"
    assert horizon_bucket(37) == "36-48h"
    assert horizon_bucket(50) == "48-72h"


def timedelta_24h():
    from datetime import timedelta

    return timedelta(hours=24)


def plus_1h():
    from datetime import timedelta

    return timedelta(hours=1)
