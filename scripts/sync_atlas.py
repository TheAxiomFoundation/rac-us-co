#!/usr/bin/env python3
"""Sync the rac-us-co corpus into Atlas/Supabase."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

import requests


ROOT = Path(__file__).resolve().parents[1]
WAVES_DIR = ROOT / "waves"
SOURCE_ROOT = ROOT / "sources"
ROOT_SEGMENTS = ("regulation", "statute")
REGULATION_PDF_URL = (
    "https://www.coloradosos.gov/CCR/GenerateRulePdf.do?fileName=9%20CCR%202503-6&ruleVersionId=11535"
)
REGULATION_TITLES = {
    "9-CCR-2503-6": "9 CCR 2503-6 Colorado Works Program",
}
STATUTE_COLLECTION_TITLES = {
    "crs": "Colorado Revised Statutes",
}
STATUTE_SECTION_TITLES = {
    "26-2-703": "Definitions",
    "26-2-709": "Benefits",
}
ROOT_LABELS = {
    "regulation": "Regulations",
    "statute": "Statutes",
}


def deterministic_id(citation_path: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"atlas:{citation_path}"))


def natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def extract_embedded_source(rac_text: str) -> str:
    match = re.match(r'\s*"""(.*?)"""\s*', rac_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_effective_date(text: str) -> str | None:
    editorial = re.search(r"effective date of (\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if editorial:
        return editorial.group(1)
    snapshot = re.search(r"retrieved on (\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if snapshot:
        return snapshot.group(1)
    return None


def all_repo_rac_paths() -> list[str]:
    paths: list[str] = []
    for root_segment in ROOT_SEGMENTS:
        root_dir = ROOT / root_segment
        if not root_dir.exists():
            continue
        for path in root_dir.rglob("*.rac"):
            if path.name.endswith(".rac.test"):
                continue
            paths.append(str(path.relative_to(ROOT)))
    return sorted(paths, key=natural_key)


def build_boundaries(repo_rac_path: str) -> list[list[str]]:
    no_suffix = repo_rac_path.removesuffix(".rac")
    parts = no_suffix.split("/")
    return [parts[:i] for i in range(1, len(parts) + 1)]


def latest_wave_by_path() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for manifest_path in sorted(WAVES_DIR.glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text())
        wave = data.get("wave", manifest_path.parent.name)
        for entry in data.get("encoded_files", []):
            path = entry.get("path")
            if path:
                mapping[path] = wave
    return mapping


def source_slice_for_path(repo_rac_path: str) -> str | None:
    slice_path = SOURCE_ROOT / "slices" / repo_rac_path.removesuffix(".rac")
    txt_path = slice_path.with_suffix(".txt")
    if txt_path.exists():
        return str(txt_path.relative_to(ROOT))
    return None


def infer_leaf_heading(repo_rac_path: str, body: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if repo_rac_path.startswith("regulation/"):
        heading_lines = [
            line
            for line in lines
            if re.match(r"^(?:\([A-Za-z0-9.]+\)|[A-Z]\.|[IVXLC]+\.)", line)
        ]
        if heading_lines:
            return heading_lines[-1]
        if len(lines) >= 3:
            return lines[2]
    if repo_rac_path.startswith("statute/"):
        quoted = re.search(r'"([^"]+)"', body)
        if quoted:
            return quoted.group(1)
        if len(lines) >= 3:
            return lines[2].strip('"')
        if len(lines) >= 2:
            return lines[1]
    return Path(repo_rac_path).stem


def boundary_heading(boundary: list[str], repo_rac_path: str | None, body: str | None) -> str:
    root = boundary[0]
    if len(boundary) == 1:
        return ROOT_LABELS[root]

    if root == "regulation":
        if len(boundary) == 2:
            return REGULATION_TITLES.get(boundary[1], boundary[1].replace("-CCR-", " CCR "))
        if body:
            lines = [line.strip() for line in body.splitlines() if line.strip()]
            index = min(len(boundary), len(lines)) - 1
            if 0 <= index < len(lines):
                return lines[index]
        return boundary[-1]

    if len(boundary) == 2:
        return STATUTE_COLLECTION_TITLES.get(boundary[1], boundary[1].upper())
    if len(boundary) == 3:
        return STATUTE_SECTION_TITLES.get(boundary[2], boundary[2])
    if body:
        return infer_leaf_heading(repo_rac_path or "/".join(boundary), body)
    return boundary[-1]


def source_url_for_path(repo_rac_path: str) -> str | None:
    parts = Path(repo_rac_path).parts
    if not parts:
        return None
    if parts[0] == "regulation":
        return REGULATION_PDF_URL
    if parts[0] == "statute" and len(parts) >= 3 and parts[1] == "crs":
        return f"https://colorado.public.law/statutes/crs_{parts[2]}"
    return None


def build_rules() -> list[dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    children_by_parent: dict[str | None, set[str]] = defaultdict(set)

    for repo_rac_path in all_repo_rac_paths():
        rac_file = ROOT / repo_rac_path
        body = extract_embedded_source(rac_file.read_text())
        effective_date = extract_effective_date(body)
        slice_path = source_slice_for_path(repo_rac_path)
        boundaries = build_boundaries(repo_rac_path)
        parent_citation: str | None = None
        for index, boundary in enumerate(boundaries):
            citation_path = "us-co/" + "/".join(boundary)
            is_leaf = index == len(boundaries) - 1
            node = nodes.get(citation_path)
            if node is None:
                node = {
                    "id": deterministic_id(citation_path),
                    "jurisdiction": "us-co",
                    "doc_type": boundary[0],
                    "parent_id": deterministic_id(parent_citation) if parent_citation else None,
                    "level": len(boundary) - 1,
                    "ordinal": None,
                    "heading": boundary_heading(boundary, repo_rac_path if is_leaf else None, body if is_leaf else None),
                    "body": None,
                    "effective_date": None,
                    "repeal_date": None,
                    "source_url": source_url_for_path(repo_rac_path),
                    "source_path": None,
                    "rac_path": None,
                    "has_rac": False,
                    "citation_path": citation_path,
                    "line_count": 0,
                }
                nodes[citation_path] = node
            if is_leaf:
                node["heading"] = infer_leaf_heading(repo_rac_path, body)
                node["body"] = body or None
                node["effective_date"] = effective_date
                node["source_url"] = source_url_for_path(repo_rac_path)
                node["source_path"] = slice_path or None
                node["rac_path"] = repo_rac_path
                node["has_rac"] = True
                node["line_count"] = len(body.splitlines()) if body else 0
            children_by_parent[parent_citation].add(citation_path)
            parent_citation = citation_path

    for parent_citation, child_paths in children_by_parent.items():
        sorted_paths = sorted(child_paths, key=lambda path: natural_key(path.split("/")[-1]))
        for ordinal, child_path in enumerate(sorted_paths, start=1):
            nodes[child_path]["ordinal"] = ordinal

    return sorted(nodes.values(), key=lambda row: (row["level"], natural_key(row["citation_path"])))


def build_encoding_runs() -> list[dict[str, Any]]:
    now = datetime.now(UTC).isoformat()
    wave_by_path = latest_wave_by_path()
    rows: list[dict[str, Any]] = []
    for repo_rac_path in all_repo_rac_paths():
        rac_path = ROOT / repo_rac_path
        rows.append(
            {
                "id": f"rac-us-co:{repo_rac_path}",
                "timestamp": now,
                "citation": "us-co/" + repo_rac_path.removesuffix(".rac"),
                "file_path": repo_rac_path,
                "complexity": {},
                "iterations": [],
                "total_duration_ms": None,
                "predicted_scores": None,
                "final_scores": None,
                "agent_type": "manual-repo",
                "agent_model": None,
                "rac_content": rac_path.read_text(),
                "session_id": None,
                "synced_at": now,
                "data_source": "manual_estimate",
                "has_issues": False,
                "note": f"Imported from rac-us-co {wave_by_path.get(repo_rac_path, 'manual-state')}",
                "autorac_version": None,
            }
        )
    return rows


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def post_json(url: str, headers: dict[str, str], rows: list[dict[str, Any]]) -> None:
    response = requests.post(url, headers=headers, json=rows, timeout=180)
    response.raise_for_status()


def sync_rules(rules: list[dict[str, Any]], service_key: str, supabase_url: str, batch_size: int) -> None:
    url = supabase_url.rstrip("/") + "/rest/v1/rules"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Accept-Profile": "arch",
        "Content-Profile": "arch",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for rule in rules:
        grouped[int(rule["level"])].append(rule)
    for level in sorted(grouped):
        for batch in chunked(grouped[level], batch_size):
            post_json(url, headers, batch)


def sync_encoding_runs(rows: list[dict[str, Any]], service_key: str, supabase_url: str, batch_size: int) -> None:
    url = supabase_url.rstrip("/") + "/rest/v1/encoding_runs"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    for batch in chunked(rows, batch_size):
        post_json(url, headers, batch)


def delete_managed_rules(service_key: str, supabase_url: str) -> None:
    url = (
        supabase_url.rstrip("/")
        + "/rest/v1/rules?citation_path=like."
        + quote("us-co/%", safe="")
    )
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept-Profile": "arch",
        "Content-Profile": "arch",
        "Prefer": "count=exact,return=minimal",
    }
    response = requests.delete(url, headers=headers, timeout=180)
    response.raise_for_status()


def delete_managed_encoding_runs(service_key: str, supabase_url: str) -> None:
    url = (
        supabase_url.rstrip("/")
        + "/rest/v1/encoding_runs?id=like."
        + quote("rac-us-co:%", safe="")
    )
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Prefer": "count=exact,return=minimal",
    }
    response = requests.delete(url, headers=headers, timeout=180)
    response.raise_for_status()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-rules", action="store_true")
    parser.add_argument("--skip-encodings", action="store_true")
    parser.add_argument("--append-only", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase_url = os.environ.get("RAC_SUPABASE_URL")
    service_key = os.environ.get("RAC_SUPABASE_SECRET_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("RAC_SUPABASE_URL and RAC_SUPABASE_SECRET_KEY are required")

    rules = build_rules()
    encodings = build_encoding_runs()
    print(f"Prepared {len(rules)} arch.rules rows")
    print(f"Prepared {len(encodings)} encoding_runs rows")

    if args.dry_run:
        sample = {
            "rule": rules[0],
            "encoding": {k: encodings[0][k] for k in ["id", "citation", "file_path", "note"]},
        }
        print(json.dumps(sample, indent=2))
        return 0

    if not args.append_only:
        if not args.skip_rules:
            delete_managed_rules(service_key, supabase_url)
        if not args.skip_encodings:
            delete_managed_encoding_runs(service_key, supabase_url)

    if not args.skip_rules:
        sync_rules(rules, service_key, supabase_url, args.batch_size)
        print("Synced arch.rules")
    if not args.skip_encodings:
        sync_encoding_runs(encodings, service_key, supabase_url, args.batch_size)
        print("Synced encoding_runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
