"""Plain-Python extract helpers (landing zone). Spark turns landing files into Bronze."""
import hashlib
import json
import logging
import os
import time

import requests

from include import config

log = logging.getLogger(__name__)


def _get(url, params=None, stream=False, retries=4):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=60, stream=stream,
                             headers={"User-Agent": "trustgraph-demo/0.1"})
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            wait = 2 ** attempt
            log.warning("GET %s failed (%s); retry in %ss", url, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}")


def download_olist():
    """Download Olist CSVs into landing/olist; skip files already present (idempotent)."""
    out = f"{config.LANDING}/olist"
    os.makedirs(out, exist_ok=True)
    for name in config.OLIST_FILES:
        dest = f"{out}/{name}"
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            log.info("have %s", name)
            continue
        tmp = dest + ".part"
        h = hashlib.sha256()
        with _get(f"{config.OLIST_BASE}/{name}", stream=True) as r, open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
        os.replace(tmp, dest)
        log.info("downloaded %s sha256=%s", name, h.hexdigest()[:16])


def fetch_fx(start, end, base="USD", symbols="BRL,EUR,GBP,JPY", out_name=None):
    """Frankfurter time series -> landing/fx/<name>.json (one JSON object per rate-row)."""
    r = _get(f"{config.FX_API}/{start}..{end}", params={"base": base, "symbols": symbols}).json()
    rows = [{"date": d, "base": base, "currency": c, "rate": v}
            for d, rates in r["rates"].items() for c, v in rates.items()]
    out = f"{config.LANDING}/fx"
    os.makedirs(out, exist_ok=True)
    path = f"{out}/{out_name or f'{start}_{end}'}.json"
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    log.info("fx: %d rows -> %s", len(rows), path)
    return len(rows)


def fetch_cfpb_day(ds, page_size=5000, max_pages=100):
    """Complaints received on `ds` -> landing/cfpb/ds=<ds>/complaints.json (JSON lines).

    Uses search_after (not from/size, which Elasticsearch caps at 10k rows).
    Idempotent: the file for a given day is rewritten wholesale on every run.
    """
    rows, after, total = [], None, None
    for _ in range(max_pages):
        params = {"date_received_min": ds, "date_received_max": ds, "size": page_size,
                  "sort": "created_date_asc", "no_aggs": "true"}
        if after:
            params["search_after"] = after
        r = _get(config.CFPB_API, params=params).json()
        hits = r["hits"]["hits"]
        total = r["hits"]["total"]["value"]
        rows.extend(h["_source"] for h in hits)
        if len(hits) < page_size:
            break
        after = "_".join(str(x) for x in hits[-1]["sort"])
    if len(rows) != total:
        raise RuntimeError(f"cfpb {ds}: pulled {len(rows)} of {total} complaints")
    out = f"{config.LANDING}/cfpb/ds={ds}"
    os.makedirs(out, exist_ok=True)
    with open(f"{out}/complaints.json", "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    log.info("cfpb %s: %d complaints", ds, len(rows))
    return len(rows)
