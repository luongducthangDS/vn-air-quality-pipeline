-- CAMS global runs on a ~0.4° (~45 km) grid. Two cities inside the same cell get byte-identical series
-- even though the API echoes different coordinates (Hanoi and Bac Ninh did). Such a pair adds no information
-- and double-counts that cell in every cross-city number, so fail the build.
select a.city as city_a, b.city as city_b, count(*) as hours,
       avg((a.pm2_5 = b.pm2_5)::int) as share_identical
from {{ ref('stg_air_quality_hourly') }} a
join {{ ref('stg_air_quality_hourly') }} b
  on a.measured_at = b.measured_at and a.city < b.city
group by all
having avg((a.pm2_5 = b.pm2_5)::int) > 0.95
