select city, name_vi, region, lat, lon
from {{ ref('cities') }}
