"""Record the API responses the web app needs into web/public/snapshot.json.

The web app falls back to this file when the live backend is unreachable (see lib/api.ts),
so judges can still browse real data. Run it with the API (localhost:8000) and the web dev
server (localhost:3000) both up; it drives a headless browser through every page.

    python3 web/scripts/capture_snapshot.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, sync_playwright

API = "http://localhost:8000"
WEB = "http://localhost:3000"
OUT = Path(__file__).resolve().parents[1] / "public" / "snapshot.json"
EXAMPLE_SEARCHES = ["saplings being planted", "flooded road", "solar panels", "children in a classroom"]


def get(path: str):
    return json.load(urllib.request.urlopen(API + path))


def all_assets(project_id: str) -> list[dict]:
    out, cursor = [], None
    while True:
        q = f"/api/assets?project_id={project_id}&limit=60" + (f"&cursor={cursor}" if cursor else "")
        page = get(q)
        out += page["items"]
        cursor = page["next_cursor"]
        if not cursor:
            return out


def backfill(snapshot: dict[str, object], assets: list, comparisons: list, reports: list) -> None:
    """Fetch detail endpoints directly for anything the browser pass missed (e.g. a slow call)."""
    paths = [f"/api/reports/{r['id']}" for r in reports]
    paths += [f"/api/reports/{r['id']}/campaign-kit" for r in reports if r["status"] == "ready"]
    paths += [f"/api/comparisons/{c['id']}" for c in comparisons]
    paths += [f"/api/assets/{a['id']}" for a in assets]
    added = 0
    for path in paths:
        if f"GET {path}" not in snapshot:
            try:
                snapshot[f"GET {path}"] = get(path)
                added += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  could not backfill {path}: {exc}")
    print(f"Backfilled {added} responses")


def main() -> None:
    snapshot: dict[str, object] = {}

    def record(response) -> None:
        req = response.request
        if not response.url.startswith(API) or response.status != 200 or "/health" in response.url:
            return
        parts = urlsplit(response.url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        key = f"GET {path}" if req.method == "GET" else f"{req.method} {path} {req.post_data or ''}"
        try:
            snapshot[key] = response.json()
        except Exception:  # noqa: BLE001 - non-JSON bodies aren't needed
            pass

    projects = get("/api/projects")["items"]
    sites, assets, comparisons, reports = [], [], [], []
    for p in projects:
        sites += get(f"/api/projects/{p['id']}/sites")["items"]
        assets += all_assets(p["id"])
        comparisons += get(f"/api/projects/{p['id']}/comparisons")["items"]
        reports += get(f"/api/projects/{p['id']}/reports")["items"]
    tags = sorted({t["tag"] for a in assets for t in a["tags"]})

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("response", record)

        def visit(path: str, wait: int = 2500) -> Page:
            page.goto(WEB + path)
            page.wait_for_timeout(wait)
            return page

        def click_all(name: str, wait: int = 1200) -> None:
            buttons = page.get_by_role("button", name=name)
            for i in range(buttons.count()):
                try:
                    buttons.nth(i).click(timeout=3000)
                    page.wait_for_timeout(wait)
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                except Exception:  # noqa: BLE001
                    pass

        def load_more() -> None:
            for _ in range(10):
                more = page.get_by_role("button", name="Load more")
                if more.count() == 0:
                    return
                more.first.click()
                page.wait_for_timeout(2000)

        for path in ["/", "/projects", "/sites", "/comparisons", "/reports", "/upload", "/how-it-works", "/credits"]:
            visit(path, 6000 if path == "/" else 3000)

        visit("/library", 4000)
        load_more()
        for tag in tags:
            visit(f"/library?tag={tag}", 1500)
        for s in sites:
            visit(f"/library?project={s['project_id']}&site={s['id']}", 1500)

        for p in projects:
            visit(f"/projects/{p['id']}")
            visit(f"/projects/{p['id']}/library", 3000)
            load_more()
            visit(f"/projects/{p['id']}/upload", 1500)
        for s in sites:
            visit(f"/sites/{s['id']}/compare", 3000)
        for c in comparisons:
            visit(f"/comparisons/{c['id']}", 3000)
            click_all("Lineage")
        for r in reports:
            visit(f"/reports/{r['id']}", 5000)
            click_all("Lineage")
            visit(f"/reports/{r['id']}/print", 2500)
        for i, a in enumerate(assets, 1):
            visit(f"/assets/{a['id']}", 1800)
            click_all("Lineage", 1000)
            if i % 20 == 0:
                print(f"  assets {i}/{len(assets)}")

        visit("/search", 2000)
        for q in EXAMPLE_SEARCHES:
            page.get_by_text(f"“{q}”").first.click()
            page.wait_for_timeout(4000)
            page.goto(WEB + "/search")
            page.wait_for_timeout(1500)

        browser.close()

    backfill(snapshot, assets, comparisons, reports)
    OUT.write_text(json.dumps(snapshot, separators=(",", ":")))
    print(f"Wrote {len(snapshot)} responses, {OUT.stat().st_size / 1024:.0f} KB -> {OUT}")


if __name__ == "__main__":
    import sys

    if "--backfill-only" in sys.argv:
        # Top up an existing snapshot without re-running the browser pass.
        data = json.loads(OUT.read_text())
        ps = get("/api/projects")["items"]
        a_, c_, r_ = [], [], []
        for p in ps:
            a_ += all_assets(p["id"])
            c_ += get(f"/api/projects/{p['id']}/comparisons")["items"]
            r_ += get(f"/api/projects/{p['id']}/reports")["items"]
        backfill(data, a_, c_, r_)
        OUT.write_text(json.dumps(data, separators=(",", ":")))
        print(f"{len(data)} responses, {OUT.stat().st_size / 1024:.0f} KB")
    else:
        main()
