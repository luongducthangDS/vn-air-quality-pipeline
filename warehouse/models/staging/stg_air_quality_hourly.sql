-- One row per city per hour (Vietnam local time, GMT+7), typed and flattened from the API's column arrays.
with src as (
    select
        _city as city,
        cast(_ingested_at as timestamptz) as ingested_at,
        hourly
    from {{ source('open_meteo', 'air_quality_raw') }}
),

flat as (
    -- unnest() calls in one SELECT zip the parallel arrays row by row
    select
        city,
        ingested_at,
        cast(unnest(hourly.time) as timestamp) as measured_at,
        unnest(hourly.pm2_5) as pm2_5,
        unnest(hourly.pm10) as pm10,
        unnest(hourly.nitrogen_dioxide) as no2,
        unnest(hourly.ozone) as o3,
        unnest(hourly.carbon_monoxide) as co,
        unnest(hourly.sulphur_dioxide) as so2,
        unnest(hourly.us_aqi) as us_aqi
    from src
)

select
    city,
    measured_at,
    cast(measured_at as date) as measured_date,
    pm2_5, pm10, no2,
    -- the feed uses -1.0 as a missing-value sentinel for ozone (found by assert_values_physically_plausible)
    case when o3 < 0 then null else o3 end as o3,
    co, so2,
    cast(us_aqi as integer) as us_aqi,
    ingested_at
from flat
-- the API pads the current day with forecast hours; keep only hours already past at ingest time
where measured_at <= cast(timezone('Asia/Ho_Chi_Minh', ingested_at) as timestamp)
  and pm2_5 is not null
