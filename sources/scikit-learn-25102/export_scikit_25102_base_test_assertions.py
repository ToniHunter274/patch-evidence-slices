#!/usr/bin/env python3
"""Extract unchanged base-commit test excerpts, with full-file SHA-256.

This creates source-only records. It does not execute code or make causal claims.
Use Python 3.9+; standard library only. Prefer --repo for a local clone; otherwise
downloads immutable URLs at the pinned historical scikit-learn base commit.
"""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COMMIT = 'f9a1cf072da9d7375d6c2163f68a6038b13b310f'
REPO = 'https://github.com/scikit-learn/scikit-learn'
INSTANCE = 'scikit-learn__scikit-learn-25102'
SOURCES = [
    ('sklearn/preprocessing/tests/test_encoders.py', [(1975, 1992)]),
    ('sklearn/compose/tests/test_column_transformer.py', [(1946, 1972), (2099, 2135)]),
]

def source_record(path, ranges, repo=None):
    raw_url = f'https://raw.githubusercontent.com/scikit-learn/scikit-learn/{COMMIT}/{path}'
    if repo is not None:
        raw = subprocess.run(['git', 'show', f'{COMMIT}:{path}'], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    else:
        request = urllib.request.Request(raw_url, headers={'User-Agent': 'scikit-25102-source-extract/1.0'})
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
    if b'\0' in raw:
        raise ValueError(f'Unexpected binary content: {path}')
    source = raw.decode('utf-8')
    # splitlines(keepends=True) ensures excerpt text, including source line endings, is preserved.
    lines = source.splitlines(keepends=True)
    if len(lines) < max(end for _,end in ranges):
        raise ValueError(f'Missing requested lines in {path}: {len(lines)} lines available')
    records=[]
    for first,last in ranges:
        verbatim = ''.join(lines[first-1:last])
        records.append({
            'source_url': f'{REPO}/blob/{COMMIT}/{path}#L{first}-L{last}',
            'file_path': path,
            'source_commit': COMMIT,
            'full_file_sha256': hashlib.sha256(raw).hexdigest(),
            'full_file_byte_count': len(raw),
            'start_line': first,
            'end_line': last,
            'excerpt_sha256': hashlib.sha256(verbatim.encode('utf-8')).hexdigest(),
            'verbatim': verbatim,
        })
    return records

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('scikit_25102_base_test_assertions.json'))
    ap.add_argument('--repo', type=Path, default=None, help='Local scikit-learn clone; use git show at pinned base commit instead of downloading')
    a=ap.parse_args()
    if a.repo is not None and not (a.repo / '.git').exists():
        raise SystemExit(f'Not a local Git clone: {a.repo}')
    excerpts=[]
    for path,ranges in SOURCES:
        data = source_record(path,ranges,repo=a.repo)
        for item in data:
            print(f'VERIFIED {path} lines {item["start_line"]}-{item["end_line"]}: '
                  f'full file SHA-256 {item["full_file_sha256"]}')
        excerpts.extend(data)
    doc={'scope': 'verbatim source excerpts only; no causal interpretation',
         'instance_id': INSTANCE,
         'repository': REPO,
         'base_commit': COMMIT,
         'records': excerpts}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    print('CREATED',a.out,'records:',len(excerpts))
    print('JSON SHA-256', hashlib.sha256(a.out.read_bytes()).hexdigest())
    print('Note: verify public download matches local JSON after committing with -text .gitattributes')

if __name__=='__main__':
    main()
