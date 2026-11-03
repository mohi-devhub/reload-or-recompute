"""Offline checks of preregistration order, coverage, source identity and budget."""
from collections import defaultdict
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def audit():
    with (ROOT/'outputs/results.jsonl').open() as f:rows=[json.loads(l) for l in f]
    rows=[r for r in rows if r.get('phase')=='phase3']
    ledger=json.loads((ROOT/'outputs/phase3_ledger.json').read_text())
    expected=json.loads((ROOT/'outputs/phase3_provenance.json').read_text())['protected_function_hashes']
    failures=[];registrations=[]
    for gpu in ['L4','A10','H100!']:
        path=ROOT/'configs'/('predictions_'+gpu+'.json')
        if not path.exists():continue
        registration=json.loads(path.read_text());registrations.append(registration)
        for source in registration['calibration_sources']:
            original=[{k:v for k,v in r.items() if k!='record_origin'} for r in rows if r.get('record_origin')=='kernel' and r.get('run_id')==source['run_id']]
            payload=''.join(json.dumps(r,allow_nan=False)+'\n' for r in original).encode()
            if hashlib.sha256(payload).hexdigest()!=source['sha256']:failures.append('Calibration source hash: '+source['run_id'])
        for run in ledger['runs']:
            if run.get('gpu')!=gpu or run['purpose']!='sweep':continue
            spec=run['specification'];commit=spec['prediction_commit']
            timestamp=int(subprocess.check_output(['git','show','-s','--format=%ct',commit],cwd=ROOT,text=True))
            committed=subprocess.check_output(['git','show',commit+':configs/predictions_'+gpu+'.json'],cwd=ROOT)
            if committed!=path.read_bytes():failures.append('Changed frozen registration: '+gpu)
            submitted=datetime.datetime.fromisoformat(run['submitted_at']).timestamp()
            if timestamp>submitted:failures.append('Commit after submission: '+run['name'])
            observed=[r for r in rows if r.get('run_id')==spec['run_id'] and r['kind']=='measurement']
            if observed and timestamp>min(r['wall_start_unix'] for r in observed):failures.append('Commit after sweep: '+run['name'])
    samples=[r for r in rows if r['kind']=='measurement']
    if any(not r['valid'] for r in samples):failures.append('Invalid measured cache restoration')
    if any(r['wall_ms']<=0 or r['cuda_event_ms']<=0 or r['peak_vram_bytes']<=0 for r in samples):failures.append('Invalid timing/physical allocation')
    for r in rows:
        if r['kind']=='source_provenance' and r['protected_function_hashes']!=expected:failures.append('Protected source mismatch: '+r['run_id'])
        if r['kind']=='cache_layout' and r['kv_bytes_per_token']!=r['kv_bytes_per_token_tensor']:failures.append('Tensor KV footprint mismatch')
    by=defaultdict(list);orders=defaultdict(dict)
    for r in samples:
        key=(r['run_id'],r['model'],r['workload'],r['prefix_tokens'],r['turn_tokens'],r['condition'])
        by[key].append(r)
        orders[key[:5]].setdefault(r['repeat'],[]).append((r['condition_position'],r['condition']))
    for reg in registrations:
        for p in reg['predictions']:
            key=tuple(p[k] for k in ['run_id','model','workload','prefix_tokens','turn_tokens','condition'])
            values=by[key]
            if sorted(r['repeat'] for r in values)!=list(range(10)):failures.append('Incomplete registered cell: '+str(key))
    sweep_ids={r['specification']['run_id'] for r in ledger['runs'] if r['purpose']=='sweep'}
    for key,rounds in orders.items():
        if key[0] in sweep_ids and len({tuple(sorted(v)) for v in rounds.values()})<2:failures.append('Condition order did not vary: '+str(key))
    main=ledger['infrastructure_reservation_usd']+sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in ledger['runs'] if r.get('gpu')!='H100!')
    h100=sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in ledger['runs'] if r.get('gpu')=='H100!')
    if main>6 or h100>4:failures.append('Cost cap exceeded')
    result=dict(kind='phase3_final_audit',phase='phase3',record_origin='audit',passed=not failures,failures=failures,
                measurement_count=len(samples),registered_cells=sum(len(r['predictions']) for r in registrations),
                main_conservative_usd=main,h100_conservative_usd=h100)
    (ROOT/'outputs/phase3_final_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));assert not failures,'Phase-three audit failed'


if __name__=='__main__':audit()
