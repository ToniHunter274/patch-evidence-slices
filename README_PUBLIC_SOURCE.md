# Exact-patch evidence extract: 33 selected software-repair patches

This is a reproducible **derived** research dataset, not 33 independently
confirmed software defects and not a Studio prompt, rubric, or answer key.

## Scope

- **33** exact-PatchDiff functionality records also accepted by the SWE-ABS
  hardened benchmark; **20** different tasks.
- **17** within-task unordered patch pairs, which are dependent observations.
- All records are exact SHA-256 patch identities, not agent-name-only joins.

## Original sources and attribution

- PatchDiff study and archived RQ1 developer-test results:
  https://github.com/ZJU-CTAG/PatchDiff/tree/0a8ed608f9f19396e1bb3f6f3dd88b0fb88b49d6
  https://doi.org/10.5281/zenodo.17074796
- SWE-ABS original research and underlying suite:
  https://github.com/OpenAgentEval/SWE-ABS/tree/26b4c736ca3d566d8395d7999304d0264abe7992
- Gold-Coupled Tests, by Phuc Phan; original data CC BY 4.0:
  https://github.com/ph-phuc/swe-bench-gold-coupling/tree/10869825a6b47e70785483083e2828a8ec683155
  Original entries: https://raw.githubusercontent.com/ph-phuc/swe-bench-gold-coupling/10869825a6b47e70785483083e2828a8ec683155/data/labels/entries.csv
  Original source SHA-256: bcdd1e2f33e41859456006d89fd5ef19a117eb6ffb6c8ebc2e07c531f63f2910

The Gold-Coupled data is attributed to its original creator under its data
license; no new license to the source research or PatchDiff files is claimed.
The public table retains original source line locators.

## Files

- `radar_33_exact_patch_evidence.csv`: the patch-unit records and full reported
  test-ID sets, with original benchmark labels and provenance pointers.
- `radar_17_within_task_pairs.csv`: original exact-set intersections, unions,
  Jaccard, and small-set containment calculations.
- `radar_20_task_summary.csv`: groups the patch-unit sample by task.
- `radar_33_manifest.json`: recorded source pins, hashes and selection.

## Essential interpretation

* `label_hardened=1` is a suite result, not a correctness certificate.
* `patchdiff_failure_test_ids_json` reports developer-test discrepancies;
  sharing test IDs does not establish a shared cause.
* `gold_task_class_CONTEXT_ONLY` is an **issue-level classification** based on
  rejected patches and MUST NOT be attributed to an accepted patch.
* The 33 records are a selected intersection, not a random sample. Repeated
  patches within an issue are not independent observations.
* SWE-ABS and Gold-Coupled are connected; do not treat them as independent
  statistical replications.

## Rebuild

Use the accompanying `radar_release_33.py` with the original local PatchDiff
and exact-SHA join. The script aborts if original SHA checks, 33 patch IDs,
17 pairs, or published hardened outcomes do not reproduce. Do not silently
edit CSVs when a check fails.
