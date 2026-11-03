"""Separate presentation by observed GPU board while preserving frozen API-tier predictions."""
from collections import defaultdict
import copy
import statistics


def hardware(rows):
    env={r['run_id']:r['environment'] for r in rows if r.get('phase')=='phase3' and r['kind']=='environment'}
    samples=defaultdict(list)
    for r in rows:
        if r.get('phase')=='phase3' and r['kind']=='telemetry_sample':samples[r['run_id']].append(r['sample'])
    out={}
    for run,e in env.items():
        name=e['gpu_names'][0];gpu='A10G' if name=='NVIDIA A10G' else e['requested_gpu']
        def values(field):return sorted({int(s[field]) for s in samples[run] if field in s})
        out[run]=dict(gpu=gpu,allocated_gpu_name=name,pcie_widths=values('pcie.link.width.current'),pcie_generations=values('pcie.link.gen.current'))
        expected={'A10':16,'A10G':8,'L4':16,'H100!':16}[gpu]
        assert out[run]['pcie_widths']==[expected], 'Observed link differs from the released board grouping: '+run
        assert max(out[run]['pcie_generations'])=={'A10':4,'A10G':4,'L4':3,'H100!':5}[gpu], 'Observed PCIe generation differs: '+run
    return out


def display(gpu):
    return {'A10':'A10 (PCIe 4 x16)','A10G':'A10G (PCIe 4 x8)','L4':'L4 (PCIe 3 x16)','H100!':'H100 (PCIe 5 x16)'}.get(gpu,gpu)


def separate(rows,canonical):
    mapping=hardware(canonical);out=[]
    for original in rows:
        r=copy.deepcopy(original)
        if r['kind'] in ['phase3_scorecard','phase3_path_scorecard']:continue
        if r['kind']=='phase3_session_spread' and r['gpu']=='A10':
            r['kind']='phase3_allocation_spread';r['compared_hardware']=[mapping[s] for s in r['sessions']]
            out.append(r);continue
        if r.get('run_id') in mapping:
            h=mapping[r['run_id']];r['requested_gpu']=r.get('gpu');r.update(h)
        out.append(r)
    scores=[r for r in out if r['kind']=='phase3_prediction_score']
    for gpu in dict.fromkeys(r['gpu'] for r in scores):
        group=[r for r in scores if r['gpu']==gpu]
        scopes=[('all',group)]+[(region,[r for r in group if r['calibration_region']==region]) for region in ['anchor','interpolation','extrapolation']]
        scopes += [('session: '+run,[r for r in group if r['run_id']==run]) for run in sorted({r['run_id'] for r in group})]
        for scope,subset in scopes:
            if not subset:continue
            decisions=[r for r in subset if r['correct'] is not None]
            out.append(dict(kind='phase3_scorecard',gpu=gpu,scope=scope,allocated_gpu_names=sorted({r['allocated_gpu_name'] for r in subset}),
                correct_decisions=sum(r['correct'] for r in decisions),resolved_decisions=len(decisions),
                unresolved_decisions=sum(r['observed_reload'] is None and r['predicted_reload'] is not None for r in subset),
                complete_cells=len(subset),median_absolute_ttft_error_ms=statistics.median(r['absolute_error_ms'] for r in subset),
                median_absolute_relative_ttft_error=statistics.median(r['absolute_relative_error'] for r in subset)))
    return out
