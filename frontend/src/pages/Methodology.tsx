import ChartCard from "../components/ChartCard";

export default function Methodology() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Methodology</h2>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Transparent, rule-based method — no black-box models. Everything below is computed from the committed
          snapshot of Elexon BMRS data (FUELHH actuals, WINDFOR forecasts).
        </p>
      </div>

      <ChartCard title="1 · Decision time & latest-available forecast">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>
            For delivery day <strong>D</strong>, the purchase decision is made on <strong>D-1</strong> at a
            configurable cutoff (default <strong>09:00 Europe/London</strong>, stored and compared in UTC).
            London↔UTC conversion uses the IANA zone rules, so DST dates are handled correctly (not relevant for
            January, which is entirely GMT, but the code and tests cover transitions).
          </li>
          <li>
            For each half-hour/hour target on day D, we take the forecast row with the{" "}
            <strong>greatest publishTime ≤ cutoff</strong>. WINDFOR revises roughly every 3 hours; this ensures the
            buyer always sees the freshest revision available at decision time.
          </li>
          <li>
            <strong>Forecast horizon</strong> = startTime − publishTime. At a 09:00 cutoff, January horizons span
            ≈15h (midnight) to ≈38h (23:00) ahead.
          </li>
        </ul>
      </ChartCard>

      <ChartCard title="2 · Aligning 30-minute actuals to hourly forecasts">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>FUELHH wind actuals arrive at 30-minute resolution (startTimes at :00 and :30).</li>
          <li>
            WINDFOR forecasts are hourly (startTime on the hour). To compare, each hourly actual is the{" "}
            <strong>mean of its two half-hours</strong>. Coverage counts are kept per hour (hours with only one
            half-hour of data are flagged in the data report rather than silently dropped).
          </li>
          <li>Errors therefore compare like-for-like hourly averages: error = forecast − actual (MW).</li>
        </ul>
      </ChartCard>

      <ChartCard title="3 · Error metrics">
        <dl className="space-y-3 text-sm text-slate-700">
          {[
            ["Bias (mean error)", "mean(forecast − actual). Positive = forecasts run high (likely under-thermal-buy); negative = underforecast wind (over-thermal-buy)."],
            ["MAE", "mean |forecast − actual| — typical miss size in MW."],
            ["RMSE", "root mean squared error — penalises large misses more; RMSE ≫ MAE indicates occasional large misses."],
            ["MAPE", "mean |error / actual| — only over hours where actual ≥ 1,000 MW to guard against near-zero actuals (division blow-up). Reported as a supplementary 'normalised error'."],
            ["P50/P90/P95 absolute error", "percentiles of the absolute error distribution — risk ceilings, e.g. '95% of hours miss by less than X MW'."],
            ["Error by hour of day", "bias/MAE per London hour of the target (equals UTC hour in January)."],
            ["Error by horizon", "bias/MAE bucketed by startTime − publishTime: 0–6, 6–12, 12–18, 18–24, 24–36, 36–48, 48–72h."],
            ["Error by generation level", "seen in the Actual-vs-Forecast scatter: points far from the diagonal at high/low wind show where the forecast struggles."],
          ].map(([t, d]) => (
            <div key={t}>
              <dt className="font-medium text-slate-900">{t}</dt>
              <dd className="text-slate-600">{d}</dd>
            </div>
          ))}
        </dl>
      </ChartCard>

      <ChartCard title="4 · Uncertainty band & risk-adjusted wind (transparent heuristic)">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>
            For all decision-time hours across January, we pool signed errors per horizon bucket and read off
            the empirical <strong>P10 and P90 of the error</strong> (forecast − actual) at the horizon relevant
            to each hour. Because actual = forecast − error, the band edges invert:
            <strong> P10(actual) = forecast − P90(error)</strong> and <strong>P90(actual) = forecast − P10(error)</strong>.
          </li>
          <li>
            The shaded band in the Forecast Explorer spans those two edges: historically, wind landed inside it
            ~80% of the time.
          </li>
          <li>
            The <strong>risk-adjusted wind figure</strong> = forecast − P90(error). Using this as the wind
            assumption in the buy means a buffer with ≈90% historical coverage against wind under-delivery
            (only 1 in 10 historical decision-time hours came in lower). This is deliberately simple and fully
            auditable.
          </li>
          <li>
            Caveat: percentile-of-error assumes the error distribution is stationary. Check the error-over-time
            chart on the Accuracy page for drift; revisit if a regime change occurs.
          </li>
        </ul>
      </ChartCard>

      <ChartCard title="5 · Assumptions & caveats">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>National-level (whole UK system) wind only; distribution-level variation is out of scope.</li>
          <li>January 2026 delivery days only, per the deliverable window.</li>          <li>Actuals dedupe by startTime keeping the latest publishTime (late corrections override earlier values).</li>
          <li>
            Forecast history is limited to what BMRS WINDFOR retains; absent revisions before 2025-12-01 are not
            reconstructed.
          </li>
          <li>All timestamps stored/returns in UTC; UI labels London time (GMT for January, so identical by
            coincidence — code is still DST-correct).</li>
        </ul>
      </ChartCard>
    </div>
  );
}
