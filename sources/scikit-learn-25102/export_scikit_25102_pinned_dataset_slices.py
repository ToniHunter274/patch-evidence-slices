#!/usr/bin/env python3
"""Publishable, neutral, version-pinned source slices for one SWE-bench instance.

Fetches the original public dataset rows, without claiming benchmark results or
inferring test coverage. Uses Hugging Face datasets + huggingface_hub. Requires
network connectivity and source access on the machine running this script.

    python -m pip install datasets huggingface_hub
    python export_scikit_25102_pinned_dataset_slices.py --out ./dataset-slices

Outputs exact selected fields and content hashes, not interpreted comparisons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

INSTANCE_ID = "scikit-learn__scikit-learn-25102"
BASE_COMMIT = "f9a1cf072da9d7375d6c2163f68a6038b13b310f"
SOURCES = (
    (
        "S1_SWE_ABS",
        "OpenAgentLab/SWE-Bench_Verified_ABS",
        "79fc07a8f4ce5e3720e069948073f5f910b7577b",
    ),
    (
        "S15_SWE_bench_Verified",
        "princeton-nlp/SWE-bench_Verified",
        "5201ca8ed3ba13911f792042414401dae3065de4",
    ),
    (
        "S17_UTBoost",
        "Bertsekas/SWE-Bench_Verified_UTBoost",
        "4747cce37dffd69ed17da141c1c4cbcac2bf804b",
    ),
)

# Test-related source fields needed for case-specific suite provenance.
# Missing fields are identified explicitly rather than synthesized.
FIELDS = (
    "instance_id", "repo", "base_commit", "version",
    "test_patch", "original_test_patch", "FAIL_TO_PASS", "PASS_TO_PASS",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def select_record(ds):
    found = None
    n = 0
    for row in ds:
        if row.get("instance_id") == INSTANCE_ID:
            n += 1
            found = row
    if n != 1:
        raise ValueError(f"Expected exactly one {INSTANCE_ID!r} record; found {n}")
    if found.get("base_commit") != BASE_COMMIT:
        raise ValueError("Instance base_commit mismatch; refusing to publish")
    return found


def export(out: Path, load_dataset_fn=None, dataset_info_fn=None):
    if load_dataset_fn is None or dataset_info_fn is None:
        try:
            from datasets import load_dataset
            from huggingface_hub import HfApi
        except ImportError as e:
            raise RuntimeError("Install prerequisites: python -m pip install datasets huggingface_hub") from e
        load_dataset_fn = load_dataset_fn or load_dataset
        dataset_info_fn = dataset_info_fn or HfApi().dataset_info

    # Fetch and validate *all* 3 pinned rows before writing any result.
    prepared = []
    for label, repo_id, revision in SOURCES:
        print(f"Retrieving {label}: {repo_id}@{revision}", flush=True)
        info = dataset_info_fn(repo_id, revision=revision)
        resolved_sha = info.sha if hasattr(info, "sha") else info["sha"]
        if resolved_sha != revision:
            raise ValueError(f"Unexpected resolved revision: {resolved_sha}; expected {revision}")
        ds = load_dataset_fn(repo_id, revision=revision, split="test")
        row = select_record(ds)
        included = {field: row[field] for field in FIELDS if field in row}
        if not isinstance(included.get("test_patch"), str):
            raise ValueError(f"{label}: missing test_patch; refusing to publish")
        record = {
            "source": {
                "dataset_repository": repo_id,
                "revision": revision,
                "dataset_split": "test",
                "original_source_url": f"https://huggingface.co/datasets/{repo_id}/tree/{revision}",
            },
            "instance_id": INSTANCE_ID,
            "selected_source_fields": included,
            "absent_source_fields": [field for field in FIELDS if field not in row],
            "source_field_sha256": {
                field: sha256(row[field].encode("utf-8"))
                for field in FIELDS if isinstance(row.get(field), str)
            },
            "full_source_row_canonical_json_sha256": sha256(canonical_json(row)),
            "extraction_method": "datasets.load_dataset at exact revision, select unique instance_id row",
        }
        raw = (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        filename = f"{label}_scikit_learn_25102.json"
        prepared.append((filename, raw, repo_id, revision))

    out.mkdir(parents=True, exist_ok=True)
    manifest = {"instance_id": INSTANCE_ID, "files": []}
    for filename, raw, repo_id, revision in prepared:
        path = out / filename
        path.write_bytes(raw)
        manifest["files"].append({
            "filename": filename,
            "published_file_sha256": sha256(raw),
            "original_dataset": repo_id,
            "original_revision": revision,
        })
        print(f"CREATED {path} sha256={sha256(raw)}", flush=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SUCCESS: three exact, pinned source-only records exported; no test run and no causal analysis")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    export(args.out)


if __name__ == "__main__":
    main()
