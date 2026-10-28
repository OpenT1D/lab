"""Export a frozen public bibliographic search; never retrieve patient records."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REUSE_RAW: Path | None = None


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def fetch(url: str, target: Path, requests: list[dict]) -> bytes:
    if REUSE_RAW is not None:
        history = json.loads((REUSE_RAW / "requests.json").read_text())
        original = next(r for r in history if r["url"] == url and r["status"] == "retrieved")
        data = (REUSE_RAW / original["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != original["sha256"]:
            raise ValueError("Changed archived search response")
        target.write_bytes(data)
        requests.append({**original, "file": target.name, "reparsed_from": str(REUSE_RAW)})
        return data
    time.sleep(0.4)
    started = datetime.now(UTC).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": "OpenT1D-literature/1"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
        target.write_bytes(data)
        requests.append(
            {
                "url": url,
                "time_utc": started,
                "file": target.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "status": "retrieved",
            }
        )
        return data
    except Exception as exc:
        requests.append({"url": url, "time_utc": started, "status": "failed", "error": str(exc)})
        raise


def europe_pmc(query: dict, cutoff: str, out: Path, requests: list[dict]) -> list[dict]:
    records, cursor, page = [], "*", 0
    while True:
        params = {
            "query": f"({query['query']}) AND FIRST_PDATE:[0001-01-01 TO {cutoff}]",
            "format": "json",
            "resultType": "core",
            "pageSize": 1000,
            "cursorMark": cursor,
        }
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
        data = json.loads(
            fetch(
                url + urllib.parse.urlencode(params), out / f"{query['id']}-{page}.json", requests
            )
        )
        batch = data.get("resultList", {}).get("result", [])
        records.extend(batch)
        if len(records) >= data["hitCount"]:
            if len(records) != data["hitCount"]:
                raise ValueError("Europe PMC count mismatch")
            query["reported_count"] = data["hitCount"]
            return records
        next_cursor = data.get("nextCursorMark")
        if not batch or not next_cursor or next_cursor == cursor:
            raise ValueError("Incomplete Europe PMC pagination")
        cursor, page = next_cursor, page + 1


def pubmed(query: dict, cutoff: str, out: Path, requests: list[dict]) -> list[dict]:
    params = {
        "db": "pubmed",
        "term": f'({query["query"]}) AND ("1800/01/01"[Date - Publication] : '
        f'"{cutoff.replace("-", "/")}"[Date - Publication])',
        "retmode": "json",
        "retmax": 10000,
        "tool": "OpenT1D_literature",
    }
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    data = json.loads(
        fetch(
            base + "esearch.fcgi?" + urllib.parse.urlencode(params),
            out / f"{query['id']}-search.json",
            requests,
        )
    )["esearchresult"]
    ids = data["idlist"]
    if len(ids) != int(data["count"]):
        raise ValueError("Incomplete PubMed UID export")
    query["reported_count"] = len(ids)
    query["query_translation"] = data.get("querytranslation")
    records = []
    for offset in range(0, len(ids), 100):
        params = {"db": "pubmed", "id": ",".join(ids[offset : offset + 100]), "retmode": "xml"}
        raw = fetch(
            base + "efetch.fcgi?" + urllib.parse.urlencode(params),
            out / f"{query['id']}-records-{offset}.xml",
            requests,
        )
        for article in ET.fromstring(raw).findall("PubmedArticle"):
            citation = article.find("MedlineCitation")
            pmid = citation.findtext("PMID")
            title = "".join(citation.find("Article/ArticleTitle").itertext())
            abstracts = citation.findall("Article/Abstract/AbstractText")
            doi = next(
                (
                    item.text
                    for item in article.findall("PubmedData/ArticleIdList/ArticleId")
                    if item.get("IdType") == "doi"
                ),
                None,
            )
            records.append(
                {
                    "id": pmid,
                    "source": "MED",
                    "pmid": pmid,
                    "title": title,
                    "doi": doi,
                    "abstractText": "\n".join("".join(a.itertext()) for a in abstracts),
                    "pubYear": citation.findtext("Article/Journal/JournalIssue/PubDate/Year"),
                }
            )
        for article in ET.fromstring(raw).findall("PubmedBookArticle/BookDocument"):
            title = article.find("ArticleTitle")
            if title is None:
                title = article.find("Book/BookTitle")
            records.append(
                {
                    "id": article.findtext("PMID"),
                    "pmid": article.findtext("PMID"),
                    "source": "MED",
                    "title": "".join(title.itertext()),
                    "abstractText": "\n".join(
                        "".join(a.itertext()) for a in article.findall("Abstract/AbstractText")
                    ),
                    "pubYear": article.findtext("Book/PubDate/Year"),
                    "pubType": "book_document",
                }
            )
    if {r["pmid"] for r in records} != set(ids):
        raise ValueError("Incomplete PubMed article export")
    return records


def main() -> None:
    global REUSE_RAW
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=HERE / "search-protocol.json")
    parser.add_argument("--reuse-raw", type=Path)
    args = parser.parse_args()
    REUSE_RAW = args.reuse_raw
    args.output.mkdir(parents=True, exist_ok=False)
    raw = args.protocol.read_bytes()
    protocol = json.loads(raw)
    queries, requests, merged = [], [], {}
    for original in protocol["queries"]:
        query = dict(original)
        try:
            function = pubmed if query["service"] == "pubmed" else europe_pmc
            records = function(
                query, protocol["publication_date_upper_bound"], args.output, requests
            )
            query.update(status="completed", retrieved_count=len(records))
            for record in records:
                key = (
                    "PMID:" + record["pmid"]
                    if record.get("pmid")
                    else "DOI:" + record["doi"].lower()
                    if record.get("doi")
                    else record["source"] + ":" + record["id"]
                )
                existing = merged.setdefault(key, {"key": key, "query_ids": [], "record": record})
                existing["query_ids"].append(query["id"])
                if len(record.get("abstractText", "")) > len(
                    existing["record"].get("abstractText", "")
                ):
                    existing["record"] = record
        except Exception as exc:
            query.update(status="failed", error=str(exc))
        queries.append(query)
        save(args.output / "requests.json", requests)
        save(args.output / "queries.json", queries)
    values = sorted(merged.values(), key=lambda r: r["key"])
    save(args.output / "screening-input.json", values)
    bibliography = []
    for value in values:
        record = value["record"]
        bibliography.append(
            {
                "key": value["key"],
                "query_ids": value["query_ids"],
                **{
                    field: record.get(field)
                    for field in ("title", "pmid", "doi", "pmcid", "pubYear", "authorString")
                },
            }
        )
    save(args.output / "bibliography.json", bibliography)
    summary = {
        "protocol_sha256": hashlib.sha256(raw).hexdigest(),
        "search_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "finished_utc": datetime.now(UTC).isoformat(),
        "queries": queries,
        "unique_records": len(values),
        "requests": requests,
    }
    save(args.output / "manifest.json", summary)
    print(json.dumps({"queries": queries, "unique_records": len(values)}, indent=2))


if __name__ == "__main__":
    main()
