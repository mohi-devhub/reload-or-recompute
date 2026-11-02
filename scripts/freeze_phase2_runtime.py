"""Freeze observed model revisions and the actual Kaggle image for reproduction."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'outputs/phase2_results.jsonl'
if not source.exists():source=ROOT/'outputs/results.jsonl'
rows=[json.loads(line) for line in source.read_text().splitlines()]
ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
full={r['specification']['run_id'] for r in ledger['runs'] if r['purpose']=='sweep' and r['status']=='fetched'}
configs=[r for r in rows if r['kind']=='model_config']
# Prefer a measured sweep over its earlier calibration when both are available.
configs.sort(key=lambda r:r['run_id'] in full)
revisions={r['model']:r['model_revision'] for r in configs}
assert all(isinstance(value,str) and len(value)==40 for value in revisions.values())
image=next(r['saved_kernel_metadata']['docker_image'] for r in ledger['runs'] if r['name']=='main-session-1')
(ROOT/'configs/model_revisions.json').write_text(json.dumps(revisions,indent=2,sort_keys=True)+'\n')
(ROOT/'configs/phase2_runtime.json').write_text(json.dumps(dict(docker_image=image),indent=2)+'\n')
print('Frozen observed revisions and Kaggle image')
