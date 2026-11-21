#!/usr/bin/env python3
"""Verify and export the two *unchanged* model_patch strings from PatchDiff v5.

Inputs: locally downloaded PatchDiff_0115_1.zip, Zenodo record 18258368.
Outputs: two .diff files + provenance.json (source only, no analysis).
Python >= 3.9; standard library only; no network access or code execution.

Usage:
    python extract_scikit_25102_patch_code.py \
      --archive "$HOME/Downloads/PatchDiff_0115_1.zip" \
      --out "$HOME/Downloads/scikit-25102-public-patches"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

INSTANCE = "scikit-learn__scikit-learn-25102"
PATCHDIFF_COMMIT = "0a8ed608f9f19396e1bb3f6f3dd88b0fb88b49d6"
ZENODO_URL = "https://zenodo.org/records/18258368"
ARCHIVE_MD5 = "c99c9e842c72ed14b9c206a97e84dff2"

PATCHES = {
    "P1": {
        "out_name": "P1_openhands_exact.diff",
        "pred_member": "PatchDiff/data/tool_results/20241029_OpenHands-CodeAct-2.1-sonnet-20241022_verified/all_preds.jsonl",
        "pred_git_blob_sha1": "f617418f9206ceac6d6bb7ad7316b13ca3ac3d8d",
        "pred_line": 366,
        "patch_sha256": "b9dca3258cfe7ca10e4bf7a8e158c485e39740a26fadc5fd85c84998692712ed",
    },
    "P2": {
        "out_name": "P2_learn_by_interact_directory_exact.diff",
        "pred_member": "PatchDiff/data/tool_results/20250110_learn_by_interact_claude3.5/all_preds.jsonl",
        "pred_git_blob_sha1": "e3015da56382a3ef7cd9375e83c6e5cc8d059415",
        "pred_line": 185,
        "patch_sha256": "16474b0397fd7f896ace7e6bbfd966dbd4e6d797554204930e2f4caa839d7920",
    },
}


def digest_bytes(algorithm: str, b: bytes) -> str:
    return hashlib.new(algorithm, b).hexdigest()


def git_blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode("ascii") + b"\0" + b).hexdigest()


def archive_md5(path: Path) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_prediction(raw: bytes, *, expected_line: int) -> tuple[dict, int]:
    matching = []
    for n, line in enumerate(raw.splitlines(), start=1):
        if INSTANCE.encode("utf-8") not in line:
            continue
        candidate = json.loads(line)
        if candidate.get("instance_id") == INSTANCE:
            matching.append((candidate, n))
    if len(matching) != 1:
        raise ValueError(f"Expected one prediction for {INSTANCE}, found {len(matching)}")
    obj, n = matching[0]
    if n != expected_line:
        raise ValueError(f"Prediction moved from line {expected_line} to {n}")
    return obj, n


def changed_files(patch: str) -> list[str]:
    return [line.partition(" b/")[2] for line in patch.splitlines()
            if line.startswith("diff --git a/") and " b/" in line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        default=Path.home() / "Downloads" / "PatchDiff_0115_1.zip")
    parser.add_argument("--out", type=Path,
                        default=Path.home() / "Downloads" / "scikit-25102-public-patches")
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.error(f"Archive missing: {args.archive}")
    if args.out.exists():
        parser.error(f"Output already exists: {args.out}. Use a new empty output path.")

    actual_md5 = archive_md5(args.archive)
    if actual_md5 != ARCHIVE_MD5:
        raise ValueError(f"Published ZIP MD5 mismatch: {actual_md5} != {ARCHIVE_MD5}")

    extracted = {}
    manifest = {
        "scope": "Literal model_patch bytes extracted from original public prediction rows; no derived analysis",
        "instance_id": INSTANCE,
        "source": {
            "zenodo_record": ZENODO_URL,
            "archive": "PatchDiff_0115_1.zip",
            "archive_md5": ARCHIVE_MD5,
            "patchdiff_repository_commit": PATCHDIFF_COMMIT,
        },
        "patches": {},
    }
    with zipfile.ZipFile(args.archive) as z:
        for tag, spec in PATCHES.items():
            prediction_bytes = z.read(spec["pred_member"])
            actual_blob = git_blob_sha1(prediction_bytes)
            if actual_blob != spec["pred_git_blob_sha1"]:
                raise ValueError(f"{tag}: archived prediction file differs from pinned Git blob: {actual_blob}")
            obj, n = extract_prediction(prediction_bytes, expected_line=spec["pred_line"])
            patch = obj.get("model_patch")
            if not isinstance(patch, str) or not patch.startswith("diff --git a/"):
                raise ValueError(f"{tag}: expected a unified diff in model_patch")
            raw = patch.encode("utf-8")  # No added newline, no line-ending conversion
            actual_hash = digest_bytes("sha256", raw)
            if actual_hash != spec["patch_sha256"]:
                raise ValueError(f"{tag}: patch bytes do not match published SHA-256: {actual_hash}")
            extracted[spec["out_name"]] = raw
            pred_path = spec["pred_member"].removeprefix("PatchDiff/")
            manifest["patches"][tag] = {
                "filename": spec["out_name"],
                "patch_sha256": actual_hash,
                "bytes": len(raw),
                "prediction_source": {
                    "zip_member": spec["pred_member"],
                    "pinned_github_url": (
                        f"https://github.com/ZJU-CTAG/PatchDiff/blob/{PATCHDIFF_COMMIT}/"
                        f"{pred_path}#L{n}"
                    ),
                    "git_blob_sha1": actual_blob,
                    "line": n,
                    "field": "model_patch",
                    "model_name_or_path": obj.get("model_name_or_path"),
                },
                "modified_paths": changed_files(patch),
            }
            print(f"VERIFIED {tag}: {actual_hash}  {len(raw)} bytes  {spec['out_name']}")

    args.out.mkdir(parents=True, exist_ok=False)
    for filename, raw in extracted.items():
        (args.out / filename).write_bytes(raw)
    (args.out / "provenance.json").write_bytes(
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    # Recheck that the exact bytes we wrote still match the expected patch hashes.
    for tag, info in manifest["patches"].items():
        actual = digest_bytes("sha256", (args.out / info["filename"]).read_bytes())
        if actual != info["patch_sha256"]:
            raise ValueError(f"{tag}: SHA mismatch after writing output")
    print("\nSUCCESS: exact source-only export written to:", args.out.resolve())
    print("Contents: two verified .diff files plus provenance.json")
    print("No external code was executed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAILED — {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
