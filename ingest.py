"""
Land raw hourly air-quality data for Vietnamese cities from the Open-Meteo Air Quality API.

    python ingest.py              # refresh current + previous month (daily incremental run)
    python ingest.py --backfill   # every month since the API history starts (2022-08)

One gzipped JSON file per city per month, exactly as the API returned it:
    data/raw/<city>/<YYYY-MM>.json.gz
Re-running a month overwrites its file, so the job is idempotent and safe to retry.
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
VARIABLES = ["pm2_5", "pm10", "nitrogen_dioxide", "ozone", "carbon_monoxide", "sulphur_dioxide", "us_aqi"]
HISTORY_START = dt.date(2022, 8, 1)  # CAMS history on Open-Meteo is empty before this
RAW = Path("data/raw")
CITIES = Path("warehouse/seeds/cities.csv")


def months(start, end):
    """First day of every month from start's month to end's month, inclusive."""
    m = start.replace(day=1)
    while m <= end:
        yield m
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def month_end(m, today):
    nxt = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return min(nxt - dt.timedelta(days=1), today)


def fetch(lat, lon, start, end, retries=3):
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "hourly": ",".join(VARIABLES),
        "start_date": start.isoformat(), "end_date": end.isoformat(), "timezone": "Asia/Ho_Chi_Minh",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{API}?{q}", timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 5)


def land(city, month, today):
    end = month_end(month, today)
    payload = fetch(city["lat"], city["lon"], month, end)
    # lineage columns: which city/month the file is, and when it was pulled
    payload["_city"] = city["city"]
    payload["_ingested_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    path = RAW / city["city"] / f"{month:%Y-%m}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(payload, f)
    tmp.replace(path)  # atomic swap: a crash never leaves a half-written file behind
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true")
    args = p.parse_args()
    today = dt.date.today()
    start = HISTORY_START if args.backfill else (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    with open(CITIES, encoding="utf-8") as f:
        cities = list(csv.DictReader(f))
    for city in cities:
        for m in months(start, today):
            print(land(city, m, today))


if __name__ == "__main__":
    main()
