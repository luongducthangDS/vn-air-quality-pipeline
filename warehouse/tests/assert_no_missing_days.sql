{{ config(severity = 'warn') }}
-- Warn on gaps: every city should have a row for every day between its first and last day.
with bounds as (
    select city, min(measured_date) as first_day, max(measured_date) as last_day
    from {{ ref('fct_air_quality_daily') }}
    group by city
),

expected as (
    select city, cast(d as date) as measured_date
    from bounds, generate_series(first_day, last_day, interval 1 day) as t(d)
)

select e.*
from expected e
left join {{ ref('fct_air_quality_daily') }} f using (city, measured_date)
where f.city is null
