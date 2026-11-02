"""Merge accepted pilot records and phase-two observations without double counting."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
canonical=ROOT/'outputs/results.jsonl'
pilot_path=ROOT/'outputs/pilot_results.jsonl'
phase2=ROOT/'outputs/phase2_results.jsonl'
if not pilot_path.exists():
    pilot=[json.loads(line) for line in canonical.read_text().splitlines()]
    pilot=[r for r in pilot if r.get('phase')!='phase2']
    pilot_path.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in pilot))
else:
    pilot=[json.loads(line) for line in pilot_path.read_text().splitlines()]
data=[json.loads(line) for line in phase2.read_text().splitlines()]
ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
planning=json.loads((ROOT/'outputs/phase2_projection.json').read_text())
data.append(dict(schema_version=2,kind='phase2_budget_ledger',phase='phase2',ledger=ledger,
                 charged_gpu_hours=sum(r.get('actual_gpu_hours',r['reserved_gpu_hours']) for r in ledger['runs'])))
data.append(dict(schema_version=2,kind='phase2_planning_projections',phase='phase2',projections=planning))
audit=ROOT/'outputs/phase2_audit.json'
if audit.exists():data.append(json.loads(audit.read_text()))
unique=set()
for r in data:
    if r['kind']=='measurement':
        key=tuple(r[k] for k in ['run_id','model','workload','prefix_tokens','turn_tokens','condition','repeat'])
        if key in unique:raise ValueError('Duplicate phase-two sample key')
        unique.add(key)
temporary=canonical.with_suffix('.jsonl.tmp')
temporary.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in pilot+data))
temporary.replace(canonical)
print(json.dumps(dict(pilot_rows=len(pilot),phase2_rows=len(data),unique_phase2_measurements=len(unique))))
