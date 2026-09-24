-- Daily averages per city, checked against the 24-hour limits of
-- QCVN 05:2023/BTNMT (Vietnam: PM2.5 50, PM10 100 µg/m³) and WHO 2021 guidelines (PM2.5 15, PM10 45 µg/m³).
{% set min_hours = 18 %}

select
    city,
    measured_date,
    count(*) as n_hours,
    count(*) >= {{ min_hours }} as is_complete,
    round(avg(pm2_5), 1) as pm2_5,
    round(avg(pm10), 1) as pm10,
    round(avg(no2), 1) as no2,
    round(avg(o3), 1) as o3,
    round(avg(co), 1) as co,
    round(avg(so2), 1) as so2,
    max(us_aqi) as us_aqi_max,
    avg(pm2_5) > 50 as pm2_5_over_qcvn,
    avg(pm2_5) > 15 as pm2_5_over_who,
    avg(pm10) > 100 as pm10_over_qcvn
from {{ ref('stg_air_quality_hourly') }}
group by city, measured_date
