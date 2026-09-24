{{ config(severity = 'warn') }}
-- Warn when any city's newest hour is more than 2 days old: the daily job or the API has stalled.
select city, max(measured_at) as latest
from {{ ref('stg_air_quality_hourly') }}
group by city
having max(measured_at) < cast(timezone('Asia/Ho_Chi_Minh', now()) as timestamp) - interval 2 day
