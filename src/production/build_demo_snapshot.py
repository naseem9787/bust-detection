"""
Static snapshot of the /api/v1 frontend API, for a backend-free demo
(GitHub Pages). Every file is a REAL response from the production API,
called in-process - nothing is generated or edited.

Covers every request the dashboard pages can make: forecast, explanations,
historical performance and region detail for all states x lead days 1-10,
region detail for every season, plus regions, cycles and the replay case.

The file key must match snapshotKey() in frontend/src/services/api.js:
path segments + sorted query params, `cycle` dropped (the backend always
serves the most recent real archive run) and values slugified.

Usage:
    .venv/Scripts/python.exe -m src.production.build_demo_snapshot <out_dir>
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from .api import app
from .frontend_adapter import SEASON_MONTHS

PREFIX = "/api/v1"
IGNORED = {"cycle"}
IGNORED_BY_PATH = {"replay/event": {"region_id"}}   # backend ignores these for that endpoint


def slug(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(v).lower()).strip("-")


def snapshot_key(path: str, params: dict) -> str:
    path = path.strip("/")
    drop = IGNORED | IGNORED_BY_PATH.get(path, set())
    parts = [f"{k}-{slug(v)}" for k, v in sorted(params.items()) if k not in drop and v is not None]
    return "_".join(slug(s) for s in path.split("/")) + ("__" + "__".join(parts) if parts else "")


def main(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    saved, t0 = 0, time.time()
    with TestClient(app) as c:
        def grab(path: str, params: dict | None = None) -> object:
            nonlocal saved
            params = params or {}
            r = c.get(f"{PREFIX}/{path.strip('/')}" + (f"?{urlencode(params)}" if params else ""))
            if r.status_code != 200:
                print(f"  skip {path} {params}: HTTP {r.status_code}", flush=True)
                return None
            data = r.json()
            with open(os.path.join(out_dir, snapshot_key(path, params) + ".json"), "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))
            saved += 1
            return data

        regions = grab("regions")
        aliases = {}
        for r in regions:
            for form in (r["id"], r.get("shortName"), r.get("name")):
                if form:
                    aliases[slug(form)] = r["id"]
        with open(os.path.join(out_dir, "region_aliases.json"), "w", encoding="utf-8") as f:
            json.dump(aliases, f)
        grab("cycles")
        events = grab("replay/events") or []
        grab("historical-performance", {"variable": "precipitation"})
        for ev in events:
            for ld in range(1, 11):
                grab("replay/event", {"event_id": ev["eventId"], "lead_day": ld})

        ids = [r["id"] for r in regions]
        for i, rid in enumerate(ids):
            for ld in range(1, 11):
                grab("forecast", {"lead_day": ld, "region_id": rid})
                grab("explanations", {"lead_day": ld, "region_id": rid})
                grab("historical-performance", {"lead_day": ld, "region_id": rid, "variable": "precipitation"})
                for season in SEASON_MONTHS:
                    grab(f"regions/{rid}", {"lead_day": ld, "season": season})
            print(f"[{i + 1}/{len(ids)}] {rid} done - {saved} files, {(time.time() - t0) / 60:.1f} min", flush=True)
    print(f"DONE {saved} files in {(time.time() - t0) / 60:.1f} min -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/demo_snapshot")
