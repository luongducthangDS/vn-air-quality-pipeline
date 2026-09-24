{{ config(severity = 'warn') }}
-- PM2.5 is a subset of PM10, so it cannot be larger. The upstream model breaks this for ~10 hours
-- on 2023-12-14/15 (Hai Phong, HCMC, Da Nang). Too small to distort daily averages, so warn, don't block.
select city, measured_at, pm2_5, pm10
from {{ ref('stg_air_quality_hourly') }}
where pm2_5 > pm10 * 1.05 + 1
