"""Build reports/ from the dbt marts: latest.md (refreshed daily by CI), summary.json and charts."""
import datetime as dt
import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path("reports")
AQI_BANDS = [(50, "Tốt"), (100, "Trung bình"), (150, "Kém cho nhóm nhạy cảm"), (200, "Kém"), (300, "Rất kém")]


def aqi_label(v):
    return next((name for hi, name in AQI_BANDS if v <= hi), "Nguy hại")


def main():
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect("warehouse/air_quality.duckdb", read_only=True)
    q = lambda sql: con.sql(sql).df()  # noqa: E731

    last_day = q("select max(measured_date) d from fct_air_quality_daily where is_complete")["d"][0].date()

    per_city = q("""
        select c.name_vi, c.city,
               round(avg(pm2_5), 1) as pm2_5_mean,
               round(100 * avg(pm2_5_over_who::int), 1) as pct_days_over_who,
               round(100 * avg(pm2_5_over_qcvn::int), 1) as pct_days_over_qcvn,
               count(*) as days
        from fct_air_quality_daily f join dim_city c using (city)
        where is_complete
        group by all order by pm2_5_mean desc""")

    seasonal = q("""
        select city, month(measured_date) as m, avg(pm2_5) as pm
        from fct_air_quality_daily where is_complete group by all""")
    peak = seasonal.loc[seasonal.groupby("city")["pm"].idxmax()].set_index("city")["m"]
    low = seasonal.loc[seasonal.groupby("city")["pm"].idxmin()].set_index("city")["m"]
    ratio = (seasonal.groupby("city")["pm"].max() / seasonal.groupby("city")["pm"].min()).round(1)

    alerts = q("""
        select c.name_vi, a.measured_date, a.pm2_5, a.baseline_pm2_5, a.z_score
        from fct_pm25_anomaly a join dim_city c using (city)
        where is_alert order by measured_date desc""")

    week = q(f"""
        select c.name_vi, round(avg(pm2_5), 1) as pm2_5, max(us_aqi_max) as aqi_max,
               sum(pm2_5_over_qcvn::int)::int as days_over_qcvn
        from fct_air_quality_daily f join dim_city c using (city)
        where measured_date > date '{last_day}' - interval 7 day and is_complete
        group by all order by pm2_5 desc""")

    summary = {
        "data_through": str(last_day),
        "cities": [
            {**r, "peak_month": int(peak[r["city"]]), "cleanest_month": int(low[r["city"]]),
             "peak_to_low_ratio": float(ratio[r["city"]])}
            for r in per_city.to_dict("records")
        ],
        "n_alerts_total": len(alerts),
        "alerts_by_city": alerts["name_vi"].value_counts().to_dict(),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), "utf-8")

    lines = [
        f"# Chất lượng không khí — cập nhật đến {last_day}",
        "",
        "_File này do GitHub Actions tự sinh mỗi ngày. Nguồn: Open-Meteo / CAMS (số liệu mô hình, không phải trạm đo)._",
        "",
        "## 7 ngày gần nhất",
        "",
        "| Thành phố | PM2.5 TB (µg/m³) | US AQI cao nhất | Mức | Số ngày vượt QCVN |",
        "|---|---:|---:|---|---:|",
        *[f"| {r.name_vi} | {r.pm2_5} | {r.aqi_max} | {aqi_label(r.aqi_max)} | {r.days_over_qcvn} |"
          for r in week.itertuples()],
        "",
        "## Cảnh báo PM2.5 bất thường (30 ngày gần nhất)",
        "",
    ]
    recent = alerts[alerts["measured_date"].dt.date > last_day - dt.timedelta(days=30)]
    if recent.empty:
        lines.append("Không có cảnh báo.")
    else:
        lines += ["| Ngày | Thành phố | PM2.5 | Nền 28 ngày | z |", "|---|---|---:|---:|---:|"]
        lines += [f"| {r.measured_date:%Y-%m-%d} | {r.name_vi} | {r.pm2_5} | {r.baseline_pm2_5} | {r.z_score} |"
                  for r in recent.itertuples()]
    (OUT / "latest.md").write_text("\n".join(lines) + "\n", "utf-8")

    monthly = q("""
        select c.name_vi, date_trunc('month', measured_date) as month, avg(pm2_5) as pm
        from fct_air_quality_daily f join dim_city c using (city)
        where is_complete group by all order by month""")
    fig, ax = plt.subplots(figsize=(11, 5))
    for name, g in monthly.groupby("name_vi"):
        ax.plot(g["month"], g["pm"], label=name, lw=1.8)
    ax.axhline(50, color="red", ls="--", lw=1, label="QCVN 05:2023 (24h) = 50")
    ax.axhline(15, color="gray", ls=":", lw=1, label="WHO 2021 (24h) = 15")
    ax.set_title("Monthly average PM2.5 by city (µg/m³)")
    ax.legend(ncol=3, fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / "monthly_pm25.png", dpi=130)
    plt.close()

    fig, ax = plt.subplots(figsize=(9, 4.5))
    per_city.plot.barh(x="name_vi", y=["pct_days_over_who", "pct_days_over_qcvn"], ax=ax,
                       color=["#999999", "#C0392B"])
    ax.invert_yaxis()
    ax.set_xlabel("% of days")
    ax.set_ylabel("")
    ax.legend(["Over WHO 2021 (15)", "Over QCVN 05:2023 (50)"])
    ax.set_title("Share of days with 24h PM2.5 above the limit")
    plt.tight_layout()
    plt.savefig(OUT / "exceedance_share.png", dpi=130)
    plt.close()

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
