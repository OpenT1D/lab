"""Record the accessible Europe PMC citation index, including empty/failed edges."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

from search import fetch, save


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", type=int, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    requests, edges, status = [], [], []
    for pmid in args.ids:
        for kind, container, item in (
            ("references", "referenceList", "reference"),
            ("citations", "citationList", "citation"),
        ):
            entry = {"seed_pmid": pmid, "direction": kind, "round": args.round}
            try:
                page, received = 1, 0
                while True:
                    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/MED/{pmid}/{kind}?"
                    params = {"format": "json", "pageSize": 1000, "page": page}
                    data = json.loads(
                        fetch(
                            url + urllib.parse.urlencode(params),
                            args.output / f"{pmid}-{kind}-{page}.json",
                            requests,
                        )
                    )
                    batch = data.get(container, {}).get(item, [])
                    edges.extend({**entry, "record": r} for r in batch)
                    received += len(batch)
                    if received >= data["hitCount"]:
                        entry.update(
                            status="completed", count=received, api_version=data["version"]
                        )
                        break
                    if not batch:
                        raise ValueError("Incomplete citation-index pagination")
                    page += 1
            except Exception as exc:
                entry.update(status="failed", error=str(exc))
            status.append(entry)
            save(args.output / "requests.json", requests)
    save(args.output / "edges.json", edges)
    save(
        args.output / "manifest.json",
        {"finished_utc": datetime.now(UTC).isoformat(), "status": status, "requests": requests},
    )
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
