"""Freeze requested grids, calibration anchors, and explicit native-memory exclusions."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'kernels/phase3'))
from provenance import functions

MAIN='Qwen/Qwen2.5-1.5B'
MODELS=[MAIN,'Qwen/Qwen2.5-3B','unsloth/Llama-3.2-3B-Instruct','EleutherAI/pythia-1.4b','microsoft/phi-2']
RATES=[50,100,200,400,800,1600]
CONDITIONS=['prefix_only','recompute','gpu_hit','cpu_pageable','file_torch_direct','file_raw_staged']+['simulated_'+str(r)+'_MBps' for r in RATES]+['simulated_unthrottled']


def create():
    rows=[json.loads(line) for line in (ROOT/'outputs/results.jsonl').read_text().splitlines()]
    configs={r['model']:r for r in rows if r['kind']=='model_config' and r.get('phase')=='phase2' and r['model'] in MODELS}
    lengths={m:[64,256,512,1024,configs[m]['config']['max_position_embeddings']-32] for m in MODELS[1:]}
    dropped=[]
    llama=MODELS[2];native=lengths[llama][-1]
    kv=configs[llama]['kv_bytes_per_token']*native
    projected=3*kv+2*configs[llama]['parameter_count']
    for gpu in ['L4','A10']:
        for condition in CONDITIONS:
            dropped.append(dict(gpu=gpu,model=llama,workload='repeated_control',prefix_tokens=native,turn_tokens=32,
                                condition=condition,reason='projected simultaneous cache and weight footprint exceeds 24 GiB',
                                projected_reference_bytes=projected,assumed_capacity_bytes=24*1024**3))
    lengths[llama]=[64,256,512,1024]
    main=[16,64,128,256,512,1024,2048,4096,8192,16384]
    anchors={MAIN:[64,1024,8192],MODELS[1]:[64,1024,8192],llama:[64,512,1024],
             MODELS[3]:[64,512,2016],MODELS[4]:[64,512,2016]}
    plan=dict(schema_version=3,phase='phase3',kind='phase3_plan',main_model=MAIN,models=MODELS,
              rates_mb_s=RATES,conditions=CONDITIONS,main_lengths=main,control_lengths_by_model=lengths,
              calibration_lengths_by_model=anchors,dropped_cells=dropped,repeats=10,warmups=1,
              calibration_repeats=3,calibration_micro_repeats=5,main_sessions=2)
    (ROOT/'configs/phase3_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    reference=[r for r in rows if r.get('phase')=='phase2' and r.get('model') in MODELS and r['kind'] in
               ['phase2_summary','bandwidth_crossover','phase2_micro_summary','session_spread']]
    ref=dict(kind='phase3_t4_reference',phase='phase3',configs=configs,observations=reference,
             source='outputs/results.jsonl',selection='complete phase-two sweep summaries; sessions remain separate')
    (ROOT/'configs/phase3_t4_reference.json').write_text(json.dumps(ref,separators=(',',':'))+'\n')
    return plan


def specification(name,gpu,purpose,timeout,models,lengths_by_model,turns_by_model,workload,seed,registration=None):
    spec=dict(run_id='phase3-'+name,gpu=gpu,phase='phase3',purpose=purpose,models=models,
              lengths=sorted(set(length for values in lengths_by_model.values() for length in values)),
              lengths_by_model=lengths_by_model,turns=sorted(set(t for values in turns_by_model.values() for t in values)),
              turns_by_model=turns_by_model,workloads=[workload],rates_mb_s=[] if purpose=='calibration' else RATES,
              repeats=3 if purpose=='calibration' else 10,warmups=1,micro_repeats=5 if purpose=='calibration' else 10,
              seed=seed,stabilize_s=10,chunk_bytes=4194304,worker_limit_s=timeout-90,max_allocated_gpus=1,
              model_revisions=json.loads((ROOT/'configs/model_revisions.json').read_text()),
              conversation_data=json.loads((ROOT/'data/phase2_conversations.json').read_text()),
              protected_function_hashes=functions((ROOT/'kernels/phase2/runner.py').read_text()),
              continue_on_model_error=purpose=='calibration',anomaly_profile=False)
    platform=ROOT/'configs/phase3_platforms.json'
    if platform.exists():spec.update(json.loads(platform.read_text()).get(gpu,{}))
    if registration:spec.update(registration)
    return spec


if __name__=='__main__':
    plan=create();folder=ROOT/'outputs/raw/phase3/control/specs';folder.mkdir(parents=True,exist_ok=True)
    for gpu,seed in [('L4',8401),('A10',8501)]:
        # Main text calibration must use the same frozen dialogue as the main sweep.
        for group,models,workload in [('main',[MAIN],'ultrachat'),('controls',MODELS[1:],'repeated_control')]:
            name='calibration-'+gpu.lower()+'-'+group
            turns={m:([32,256] if m==MAIN else [32]) for m in models}
            timeout=420 if group=='main' else 600
            spec=specification(name,gpu,'calibration',timeout,models,{m:plan['calibration_lengths_by_model'][m] for m in models},turns,workload,seed)
            (folder/(name+'.json')).write_text(json.dumps(spec)+'\n')
    print('Frozen grid and calibration specifications')
