-- Flags days whose PM2.5 is unusually high *for that city at that time*, not just above a fixed limit.
-- z-score of log(PM2.5) against the previous 28 complete days (log because PM2.5 is right-skewed).
-- ponytail: rolling mean/stddev, not a seasonal model; a winter day in Hanoi is judged against
-- the last 4 weeks of winter, which is the point. Swap in STL residuals if seasonality starts to bite.
with daily as (
    select city, measured_date, pm2_5, ln(greatest(pm2_5, 1)) as log_pm
    from {{ ref('fct_air_quality_daily') }}
    where is_complete
),

scored as (
    select
        *,
        avg(log_pm) over w as base_mean,
        stddev_samp(log_pm) over w as base_std,
        count(*) over w as base_days
    from daily
    window w as (partition by city order by measured_date rows between 28 preceding and 1 preceding)
)

select
    city,
    measured_date,
    pm2_5,
    round(exp(base_mean), 1) as baseline_pm2_5,
    round((log_pm - base_mean) / nullif(base_std, 0), 2) as z_score,
    -- alert only when the spike is statistically unusual AND breaks the national 24h limit
    base_days >= 21 and (log_pm - base_mean) / nullif(base_std, 0) > 2.5 and pm2_5 > 50 as is_alert
from scored
