"""Audit physical work, correctness, coverage, and budget in fetched phase-two runs."""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def audit():
    ledger=json.loads((ROOT/'outputs/phase2_ledger.json').read_text())
    queue=json.loads((ROOT/'configs/phase2_queue.json').read_text())
    charge=sum(r.get('actual_gpu_hours',r['reserved_gpu_hours']) for r in ledger['runs'])
    assert charge<=10, 'Phase-two usage plus reservations exceeds the authorized cap'
    report=dict(schema_version=2,kind='phase2_audit',phase='phase2',
                used_plus_reserved_gpu_hours=charge,runs=[],pending_run_names=[],coverage_issues=[])
    recorded={r['name'] for r in ledger['runs']}
    report['pending_run_names']=[r['name'] for r in queue if r['name'] not in recorded]
    for run in ledger['runs']:
        if run['status']!='fetched':
            report['pending_run_names'].append(run['name'])
            continue
        path=ROOT/'outputs/raw/phase2'/run['name']/'phase2-output/results.jsonl'
        if not path.exists():
            assert run['gpu']=='NvidiaTeslaP100', 'Missing reference output'
            continue
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        if run['purpose']!='sweep':continue
        assert run.get('saved_source_matches_execution'), 'Saved source differs from executed source'
        assert run['saved_kernel_metadata']['is_private'], 'Kernel was not private'
        saved=ROOT/'outputs/raw/phase2'/run['name']/'source'
        metadata=json.loads((saved/'kernel-metadata.json').read_text())
        source=(saved/metadata['code_file']).read_text()
        functions='\n\n'.join(ast.get_source_segment(source,node) for node in ast.parse(source).body
                               if isinstance(node,ast.FunctionDef) and node.name!='main')
        function_hash=hashlib.sha256(functions.encode()).hexdigest()
        samples=[r for r in rows if r['kind']=='measurement']
        assert all(r['valid'] for r in samples), 'Invalid sweep measurement'
        keys=set()
        counts=Counter()
        rate_checks=0
        for r in samples:
            key=tuple(r[k] for k in ['model','workload','prefix_tokens','turn_tokens','condition','repeat'])
            assert key not in keys, 'Duplicate measured sample'
            keys.add(key)
            assert r['kv_bytes']==r['prefix_tokens']*r['kv_bytes_per_token'], 'KV byte arithmetic differs'
            assert r['dtype']=='float16' and r['concurrency']==1
            expected=r['prefix_tokens']+(0 if r['condition']=='prefix_only' else r['turn_tokens'])
            assert r['cache_length']==expected, 'Incorrect returned cache length'
            if r['condition']!='prefix_only':assert r['first_token_equal'], 'First-token disagreement'
            assert r['wall_ms']>0
            if r['condition'].startswith('simulated_'):
                assert r['simulated_bandwidth'], 'Missing simulated-bandwidth label'
                achieved=r['achieved_transport_bytes_s']
                assert achieved>0 and r['transfer_ms']>0
                target=r.get('target_bandwidth_bytes_s')
                if target is not None:
                    assert achieved<=target*1.0001, 'Rate limiter exceeded the requested rate'
                    rate_checks+=1
            if r['repeat']>=0:counts[key[:-1]]+=1
        partial=[dict(key=key,measured_repeats=n) for key,n in counts.items() if n!=10]
        if partial:report['coverage_issues'].append(dict(run=run['name'],partial_conditions=partial))
        finished=[r for r in rows if r['kind']=='shape_complete']
        observed_shapes={tuple(r[k] for k in ['model','workload','prefix_tokens','turn_tokens']) for r in finished}
        expected_shapes=set()
        spec=run['specification']
        for cfg in (r for r in rows if r['kind']=='model_config'):
            limit=cfg['config']['max_position_embeddings']
            lengths=set(spec['lengths'])
            boundary=limit-max(spec['turns'])
            if min(lengths)<boundary<max(lengths):lengths.add(boundary)
            expected_shapes.update((cfg['model'],workload,length,turn)
                                   for workload in spec['workloads'] for length in lengths
                                   for turn in spec['turns'] if length+turn<=limit)
        missing=sorted(expected_shapes-observed_shapes)
        if missing:report['coverage_issues'].append(dict(run=run['name'],missing_shapes=missing))
        for shape in finished:
            prefix=tuple(shape[k] for k in ['model','workload','prefix_tokens','turn_tokens'])
            for condition in shape['conditions']:
                assert counts[prefix+(condition,)]==10, 'Completed shape lacks ten measurements'
        complete=any(r['kind']=='run_complete' for r in rows)
        if not complete:report['coverage_issues'].append(run['name']+': no run_complete')
        report['runs'].append(dict(name=run['name'],measurements=len(samples),
                                  completed_shapes=len(finished),rate_limit_checks=rate_checks,
                                  missing_shapes=len(missing),
                                  run_complete=complete,invalid_measurements=0,
                                  reference_functions_sha256=function_hash))
    hashes=sorted({r['reference_functions_sha256'] for r in report['runs']})
    report['reference_function_hashes']=hashes
    assert len(hashes)<=1, 'Reference function source changed between sweep sessions'
    revisions={}
    for run in ledger['runs']:
        if run['status']!='fetched' or run['purpose']!='sweep':continue
        path=ROOT/'outputs/raw/phase2'/run['name']/'phase2-output/results.jsonl'
        for line in path.read_text().splitlines():
            row=json.loads(line)
            if row['kind']=='model_config':revisions.setdefault(row['model'],set()).add(row['model_revision'])
    assert all(len(values)==1 for values in revisions.values()),'Model revision changed across sweep sessions'
    report['model_revisions']={model:sorted(values) for model,values in revisions.items()}
    report['queue_complete']=not report['pending_run_names'] and not report['coverage_issues']
    output=ROOT/'outputs/phase2_audit.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':audit()
