#!/usr/bin/env python 3.11.0
# -*-coding:utf-8 -*-
# @Author  : Shuang (Twist) Song
# @Contact   : SongshGeo@gmail.com
# GitHub   : https://github.com/SongshGeo
# Website: https://cv.songshgeo.com/

"""Scrape dynasty/reign-period temporal data from data.library.sh.cn.

Two-phase scrape using curl (urllib was hanging on connection pool):
1. Page through /dynasty/search to collect every URI (88 pages, ~880 rows).
2. For each URI, download <uri>.json (HTTP 302 -> follow).

Outputs:
- data/dynasties.json          : merged dict keyed by entity URI (raw RDF/JSON shape)
- data/dynasty_temporal.csv    : flat table
- data/dynasty_raw/<id>.json   : per-entity cache for resumability
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = "https://data.library.sh.cn"
SEARCH_URL = f"{BASE}/dynasty/search"
UA = "Mozilla/5.0 (compatible; paleoflood-research/1.0)"

ONT = "http://www.library.sh.cn/ontology"
LABEL = "http://bibframe.org/vocab/label"
FIELDS = {
    "dynasty": f"{ONT}/dynasty",
    "reignTitle": f"{ONT}/reignTitle",
    "monarch": f"{ONT}/monarch",
    "monarchName": f"{ONT}/monarchName",
    "beginYear": f"{ONT}/beginYear",
    "endYear": f"{ONT}/endYear",
    "label": LABEL,
}


def log(msg: str) -> None:
    print(msg, flush=True)


def curl_post_json(url: str, form: dict, retries: int = 4) -> dict:
    data = "&".join(f"{k}={v}" for k, v in form.items())
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            out = subprocess.run(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "20",
                    "-A",
                    UA,
                    "-H",
                    "Accept: application/json",
                    "-X",
                    "POST",
                    "--data",
                    data,
                    url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(out.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            last_err = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"POST failed: {url} {form}: {last_err}")


def curl_get_json(url: str, retries: int = 4) -> dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            out = subprocess.run(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "20",
                    "-A",
                    UA,
                    "-H",
                    "Accept: application/json",
                    url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            text = out.stdout.strip()
            if not text:
                raise ValueError("empty response")
            return json.loads(text)
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
            last_err = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"GET failed: {url}: {last_err}")


def fetch_listing() -> list[dict]:
    items: list[dict] = []
    first = curl_post_json(
        SEARCH_URL,
        {"pageth": 1, "iflimit": 1, "freeText": "", "firstChar": "全部"},
    )
    pager = first["pager"]
    page_count = pager["pageCount"]
    row_count = pager["rowCount"]
    items.extend(first["detail"])
    log(f"listing: pages={page_count} expected_rows={row_count}")

    for page in range(2, page_count + 1):
        page_data = curl_post_json(
            SEARCH_URL,
            {"pageth": page, "iflimit": 1, "freeText": "", "firstChar": "全部"},
        )
        items.extend(page_data["detail"])
        if page % 10 == 0 or page == page_count:
            log(f"  listing page {page}/{page_count} (collected {len(items)})")

    log(f"listing done: {len(items)} rows")
    return items


def first_value(record: dict, predicate: str) -> str | None:
    bucket = record.get(predicate)
    if not bucket:
        return None
    return bucket[0].get("value")


def flatten(uri: str, record: dict) -> dict:
    return {
        "uri": uri,
        "dynasty": first_value(record, FIELDS["dynasty"]),
        "reignTitle": first_value(record, FIELDS["reignTitle"]),
        "monarch": first_value(record, FIELDS["monarch"]),
        "monarchName": first_value(record, FIELDS["monarchName"]),
        "beginYear": first_value(record, FIELDS["beginYear"]),
        "endYear": first_value(record, FIELDS["endYear"]),
        "label": first_value(record, FIELDS["label"]),
    }


def fetch_entity(uri: str, cache_dir: Path) -> tuple[str, dict]:
    entity_id = uri.rsplit("/", 1)[-1]
    cache_path = cache_dir / f"{entity_id}.json"
    if cache_path.exists():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return uri, payload.get(uri, {})
        except json.JSONDecodeError:
            cache_path.unlink(missing_ok=True)
    payload = curl_get_json(uri + ".json")
    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return uri, payload.get(uri, {})


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "dynasty_raw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "dynasties.json"
    csv_path = out_dir / "dynasty_temporal.csv"

    listing = fetch_listing()
    uris: list[str] = []
    seen: set[str] = set()
    for row in listing:
        u = row["uri"]
        if u in seen:
            continue
        seen.add(u)
        uris.append(u)
    log(f"unique uris: {len(uris)}")

    merged: dict[str, dict] = {}
    failures: list[tuple[str, str]] = []

    workers = 6
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_entity, uri, cache_dir): uri for uri in uris}
        for fut in as_completed(futures):
            uri = futures[fut]
            try:
                _, record = fut.result()
                merged[uri] = record
            except Exception as exc:  # noqa: BLE001
                failures.append((uri, str(exc)))
            done += 1
            if done % 50 == 0 or done == len(uris):
                log(f"  fetched {done}/{len(uris)} (failures so far: {len(failures)})")

    json_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"wrote {json_path} ({len(merged)} entities)")

    flat = [flatten(u, merged[u]) for u in uris if u in merged]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "dynasty",
                "reignTitle",
                "monarch",
                "monarchName",
                "beginYear",
                "endYear",
                "label",
                "uri",
            ],
        )
        writer.writeheader()
        writer.writerows(flat)
    log(f"wrote {csv_path} ({len(flat)} rows)")

    if failures:
        log(f"FAILED: {len(failures)} uris")
        for uri, err in failures[:10]:
            log(f"  {uri}: {err}")
        sys.exit(1 if len(failures) > len(uris) * 0.05 else 0)


if __name__ == "__main__":
    main()
