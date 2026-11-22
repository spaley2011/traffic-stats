#!/usr/bin/env python3
"""Collect GitHub traffic views for every repo you own and build shields.io badge files."""
import json
import os
import urllib.request
from pathlib import Path

API = "https://api.github.com"
TOKEN = os.environ["TRAFFIC_TOKEN"]
SKIP_FORKS = os.environ.get("SKIP_FORKS", "1") == "1"
HISTORY = Path("history.json")
BADGES = Path("badges")


def get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def my_repos():
    repos, page = [], 1
    while True:
        batch = get(f"{API}/user/repos?affiliation=owner&per_page=100&page={page}")
        if not batch:
            return repos
        repos += [r for r in batch if not (SKIP_FORKS and r["fork"])]
        page += 1


def short(n):
    for div, suffix in ((1_000_000, "M"), (1_000, "k")):
        if n >= div:
            return f"{n / div:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


def badge(path, label, n, color="blue"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schemaVersion": 1, "label": label, "message": short(n), "color": color,
    }))


def main():
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}

    for repo in my_repos():
        name = repo["full_name"]
        try:
            data = get(f"{API}/repos/{name}/traffic/views")
        except urllib.error.HTTPError as e:
            print(f"skip {name}: HTTP {e.code}")
            continue
        days = history.setdefault(name, {})
        for v in data["views"]:
            days[v["timestamp"][:10]] = {"count": v["count"], "uniques": v["uniques"]}

    HISTORY.write_text(json.dumps(history, indent=2, sort_keys=True))

    all_dates = sorted({d for days in history.values() for d in days})
    recent = set(all_dates[-14:])

    total = sum(v["count"] for days in history.values() for v in days.values())
    last14 = sum(v["count"] for days in history.values()
                 for d, v in days.items() if d in recent)

    badge(BADGES / "total-views.json", "total views", total)
    badge(BADGES / "views-14d.json", "views (14d)", last14, "brightgreen")
    for name, days in history.items():
        repo_total = sum(v["count"] for v in days.values())
        badge(BADGES / "repos" / f"{name.split('/')[1]}.json", "views", repo_total)

    print(f"{len(history)} repos | all-time {total} | last 14 days {last14}")


if __name__ == "__main__":
    main()
