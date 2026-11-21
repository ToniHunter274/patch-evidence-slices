#!/usr/bin/env python3
"""Make a source-only, self-verifying public extract for scikit-learn__scikit-learn-25102.

Input sources:
  1. The user-downloaded published PatchDiff ZIP (Zenodo 18258368).
  2. Exact pinned Gold-Coupled entries.csv (downloaded or supplied locally).

Only original per-instance RQ1 records, prediction metadata, and exact CSV rows
are copied into the output. No interpretation, answer key, or causal research.

Python >= 3.9, standard library only. Read only on source files.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

INSTANCE = 'scikit-learn__scikit-learn-25102'
PATCHDIFF_COMMIT = '0a8ed608f9f19396e1bb3f6f3dd88b0fb88b49d6'
GOLD_COMMIT = '10869825a6b47e70785483083e2828a8ec683155'
GOLD_URL = ('https://raw.githubusercontent.com/ph-phuc/swe-bench-gold-coupling/'
            + GOLD_COMMIT + '/data/labels/entries.csv')
GOLD_SHA = 'bcdd1e2f33e41859456006d89fd5ef19a117eb6ffb6c8ebc2e07c531f63f2910'
ARCHIVE_MD5 = 'c99c9e842c72ed14b9c206a97e84dff2'
SOURCES = {
  'P1': {
    'patch_sha256':'b9dca3258cfe7ca10e4bf7a8e158c485e39740a26fadc5fd85c84998692712ed',
    'rq1':'PatchDiff/results/RQ1_OpenHands_runall.json',
    'rq1_full_sha256':'9e6913c0f169d5d62261ba8266400675cdbda3f531cd6d9cc3a92d5b6465421c',
    'pred':'PatchDiff/data/tool_results/20241029_OpenHands-CodeAct-2.1-sonnet-20241022_verified/all_preds.jsonl',
  },
  'P2': {
    'patch_sha256':'16474b0397fd7f896ace7e6bbfd966dbd4e6d797554204930e2f4caa839d7920',
    'rq1':'PatchDiff/results/RQ1_LearnByInteract_runall.json',
    'rq1_full_sha256':'b6471f1b6a4d66cb3dc08c001d2a908e9a9ca179f273edb4083bfa20cd004cf7',
    'pred':'PatchDiff/data/tool_results/20250110_learn_by_interact_claude3.5/all_preds.jsonl',
  },
}

def digest(b):return hashlib.sha256(b).hexdigest()

def get_gold(path):
    if path and path.is_file():
        raw=path.read_bytes()
    else:
        req=urllib.request.Request(GOLD_URL,headers={'User-Agent':'scikit25102-source-reproducer/1.0'})
        with urllib.request.urlopen(req,timeout=90) as r:raw=r.read()
    actual=digest(raw)
    if actual!=GOLD_SHA:
        raise ValueError('Gold entries CSV SHA mismatch: got '+actual+' expected '+GOLD_SHA)
    return raw

def find_prediction(z,p):
    with z.open(p) as handle:
        for n, rawline in enumerate(handle,1):
            if INSTANCE.encode() not in rawline:continue
            obj=json.loads(rawline)
            if obj.get('instance_id')==INSTANCE:return obj,n
    raise ValueError('Prediction missing for '+p)

def get_csv_row(raw, sha):
    rdr=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    matches=[]
    for row in rdr:
        if row.get('instance_id')==INSTANCE and row.get('sha')==sha:
            matches.append((rdr.line_num,row))
    if len(matches)!=1:raise ValueError(f'Expected 1 exact Gold entry for {sha}, got {len(matches)}')
    return matches[0]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=Path,default=Path.home()/'Downloads'/'PatchDiff_0115_1.zip')
    ap.add_argument('--gold-csv',type=Path,default=None,help='Exact pinned CSV local copy, else download from GitHub')
    ap.add_argument('--out',type=Path,default=Path('scikit_25102_original_source_slice.json'))
    args=ap.parse_args()
    if not args.archive.is_file():ap.error('Archive not found: '+str(args.archive))
    gold=get_gold(args.gold_csv)
    with args.archive.open('rb') as f:
        md5 = hashlib.md5()
        for block in iter(lambda:f.read(4*1024*1024),b''):md5.update(block)
    if md5.hexdigest()!=ARCHIVE_MD5:
        raise ValueError('Archive MD5 differs from published Zenodo checksum: '+md5.hexdigest())
    result={
      'scope':'source excerpts only; no inferred defects or independent execution claims',
      'instance_id':INSTANCE,
      'sources':{
       'PatchDiff':{'archive_url':'https://zenodo.org/records/18258368',
                    'archive_zip_member':'PatchDiff_0115_1.zip',
                    'archive_zip_md5':ARCHIVE_MD5,
                    'replication_commit':PATCHDIFF_COMMIT},
       'Gold-Coupled':{'url':GOLD_URL,'commit':GOLD_COMMIT,
                       'full_csv_sha256':GOLD_SHA,
                       'csv_header':gold.decode('utf-8-sig').splitlines()[0]}
      },
      'patches':{}
    }
    with zipfile.ZipFile(args.archive) as z:
      for tag,p in SOURCES.items():
        raw=z.read(p['rq1'])
        sha=digest(raw)
        if sha!=p['rq1_full_sha256']:
            raise ValueError(f'{tag} original RQ1 full JSON changed: {sha}')
        full=json.loads(raw)
        rq1=full.get(INSTANCE)
        if not isinstance(rq1,dict):raise ValueError(f'{tag} instance missing from RQ1')
        pred,n=find_prediction(z,p['pred'])
        patch=pred.get('model_patch')
        if not isinstance(patch,str):raise ValueError(f'{tag} model_patch not a string')
        patchsha=digest(patch.encode('utf-8'))
        if patchsha!=p['patch_sha256']:
            raise ValueError(f'{tag} exact patch sha mismatch {patchsha}')
        csv_line,row=get_csv_row(gold,patchsha)
        result['patches'][tag]={
          'patch_sha256':patchsha,
          'prediction':{
            'original_member':p['pred'],
            'original_line':n,
            'original_github_url':'https://github.com/ZJU-CTAG/PatchDiff/blob/'+PATCHDIFF_COMMIT+'/'+p['pred'].removeprefix('PatchDiff/')+'#L'+str(n),
            'instance_id':pred.get('instance_id'),
            'model_name_or_path':pred.get('model_name_or_path')
          },
          'patchdiff_rq1':{
            'original_zip_member':p['rq1'],
            'full_member_sha256':sha,
            'record':rq1
          },
          'gold_coupled':{
            'original_csv_line':csv_line,
            'source_url':'https://github.com/ph-phuc/swe-bench-gold-coupling/blob/'+GOLD_COMMIT+'/data/labels/entries.csv#L'+str(csv_line),
            'original_row':row
          }
        }
        print(tag,'patch',patchsha,'prediction line',n,'Gold CSV line',csv_line,
              'RQ1 test IDs',len(rq1.get('oracle_pass_model_fail',[])))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Written:',args.out.resolve())
    print('You may publish this JSON with the script and original-source links.')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'INCOMPLETE — {type(e).__name__}: {e}',file=sys.stderr)
        raise SystemExit(1)
