# Vietnam Air Quality Pipeline

## Status (2026-11-04)

Daily CI failed from 2026-10-22 to 2026-11-04. Cause: unpinned `duckdb` moved from 1.5.6 to 2.0.0, and `stg_air_quality_hourly` then ran out of memory under the 512MB limit. Fix: exact versions in `requirements.txt`, verified locally (pytest, dbt build, report) with data through 2026-11-03.

## Gotchas

- Before upgrading `duckdb` past 1.5.6, run `dbt build` with the 512MB limit: 2.0.0 reproduces the out-of-memory error.
- The daily job ingests the current and previous month, so a failure shorter than about a month backfills itself.
- `assert_pm25_not_above_pm10` warns on 10 rows by design.
- Run dbt from the repo root, because paths in `profiles.yml` and `_sources.yml` are relative to it.
