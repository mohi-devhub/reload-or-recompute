"""Merge accepted pilot records and phase-two observations without double counting."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
canonical=ROOT/'outputs/results.jsonl'
pilot_path=ROOT/'outputs/pilot_results.jsonl'
phase2=ROOT/'outputs/phase2_results.jsonl'
later_lines=[]
if canonical.exists():
    with canonical.open() as stream:
        later_lines=[line for line in stream if json.loads(line).get('phase')=='phase3']
if not pilot_path.exists():
    pilot=[json.loads(line) for line in canonical.read_text().splitlines()]
    pilot=[r for r in pilot if r.get('phase') not in ['phase2','phase3']]
    pilot_path.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in pilot))
else:
    pilot=[json.loads(line) for line in pilot_path.read_text().splitlines()]
data=[json.loads(line) for line in phase2.read_text().splitlines()]
ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
planning=json.loads((ROOT/'outputs/phase2_projection.json').read_text())
if any(r['status'] in ['submitted','reserved'] for r in ledger['runs']):
    raise ValueError('Final consolidation requires every active reservation to be reconciled')
phase_charge=sum(r.get('actual_gpu_hours',r['reserved_gpu_hours']) for r in ledger['runs'])
assert phase_charge<=10,'Phase-two charge exceeds the authorized cap'
data.append(dict(schema_version=2,kind='phase2_budget_ledger',phase='phase2',ledger=ledger,
                 charged_gpu_hours=phase_charge))
pilot_charge=next(r['conservative_allocated_gpu_hours'] for r in pilot if r['kind']=='budget_ledger')
study_charge=pilot_charge+phase_charge
budget=dict(schema_version=2,kind='study_budget_summary',phase='phase2',
            pilot_gpu_hours=pilot_charge,phase2_gpu_hours=phase_charge,
            total_study_gpu_hours=study_charge,weekly_limit_gpu_hours=30,
            remaining_weekly_gpu_hours=30-study_charge)
data.append(budget)
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
temporary.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in pilot+data)+''.join(later_lines))
temporary.replace(canonical)
budget_doc=ROOT/'docs/BUDGET.md'
original_budget=budget_doc.read_text()
phase3_budget='\n## Phase three'+original_budget.split('\n## Phase three',1)[1] if '\n## Phase three' in original_budget else ''
text=original_budget.split('\n## Combined study total')[0]
text=text.replace('Remaining pilot allowance under the conservative process accounting:',
                  'At the pilot stop, remaining pilot allowance under conservative process accounting:')
text=text.replace('Remaining weekly allowance on that basis:', 'At the pilot stop, remaining weekly allowance on that basis:')
text+=f"\n## Combined study total\n\nPilot plus redesigned phase: **{study_charge:.6f} conservative GPU-hours**. "
text+=f"Remaining weekly allowance on this accounting basis: **{30-study_charge:.6f} GPU-hours**. "
text+='Source: `study_budget_summary` in `outputs/results.jsonl`; the completed phase is stopped.\n'
budget_doc.write_text(text+phase3_budget)
print(json.dumps(dict(pilot_rows=len(pilot),phase2_rows=len(data),unique_phase2_measurements=len(unique))))
