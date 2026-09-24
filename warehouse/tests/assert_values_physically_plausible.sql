-- Negative or absurd concentrations mean a broken feed, not bad air: fail the build so nothing gets published.
select *
from {{ ref('stg_air_quality_hourly') }}
where pm2_5 < 0 or pm10 < 0 or no2 < 0 or o3 < 0 or co < 0 or so2 < 0
   or pm2_5 > 1000
