"""Bounded Modal jobs; the reference measurement functions live in phase two."""
import json
import os
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parents[2] if modal.is_local() else Path('/study')
GPU=os.environ.get('PHASE3_GPU','L4')
LIMIT=int(os.environ.get('PHASE3_TIMEOUT','600'))
NAME=os.environ.get('PHASE3_RUN_NAME','reload-recompute-phase3')
CPU=int(os.environ.get('PHASE3_CPU','4'))
RAM=int(os.environ.get('PHASE3_MEMORY_MIB','32768'))
CACHE_NAME='reload-recompute-phase3-models-20261103'
OUTPUT_NAME='reload-recompute-phase3-results-20261103'
cache=modal.Volume.from_name(CACHE_NAME,create_if_missing=True)
outputs=modal.Volume.from_name(OUTPUT_NAME,create_if_missing=True)
image=(modal.Image.debian_slim(python_version='3.13')
       .pip_install('torch==2.11.0+cu130',index_url='https://download.pytorch.org/whl/cu130')
       .pip_install('transformers==4.51.3','safetensors==0.8.0','accelerate==1.15.0','numpy==2.4.6',
                    'huggingface-hub==0.36.2','tokenizers==0.21.4')
       .env({'HF_HOME':'/cache/hf','HF_HUB_DISABLE_PROGRESS_BARS':'1','HF_HUB_DISABLE_TELEMETRY':'1',
             'PHASE3_GPU':GPU,'PHASE3_TIMEOUT':str(LIMIT),'PHASE3_RUN_NAME':NAME,
             'PHASE3_CPU':str(CPU),'PHASE3_MEMORY_MIB':str(RAM)})
)
if modal.is_local():
    image=(image.add_local_file(ROOT/'kernels/phase2/runner.py','/study/reference.py')
           .add_local_file(ROOT/'kernels/phase3/adapter.py','/study/adapter.py')
           .add_local_file(ROOT/'kernels/phase3/provenance.py','/study/provenance.py')
           .add_local_file(ROOT/'configs/model_revisions.json','/study/revisions.json'))
app=modal.App(NAME)

@app.function(image=image,cpu=(2,2),memory=(4096,4096),volumes={'/cache':cache,'/persist':outputs},
              timeout=1200,startup_timeout=90,scaledown_window=2,max_containers=1,retries=0,single_use_containers=True)
def preload():
    import time
    from huggingface_hub import HfApi,snapshot_download
    start=time.time();selected={}
    revisions=json.loads(Path('/study/revisions.json').read_text())
    models=['Qwen/Qwen2.5-1.5B','Qwen/Qwen2.5-3B','unsloth/Llama-3.2-3B-Instruct',
            'EleutherAI/pythia-1.4b','microsoft/phi-2']
    for model in models:
        files=HfApi().list_repo_files(model,revision=revisions[model])
        weights=[f for f in files if f.endswith('.safetensors')]
        if not weights:weights=[f for f in files if f.endswith('.bin')]
        allowed=weights+[f for f in files if f.endswith(('.json','.txt','.model','.tiktoken'))]
        snapshot_download(model,revision=revisions[model],allow_patterns=allowed)
        selected[model]=dict(revision=revisions[model],weight_files=len(weights))
    cache.commit()
    result=dict(kind='phase3_preload',phase='phase3',duration_s=time.time()-start,models=selected)
    Path('/persist/preload.json').write_text(json.dumps(result))
    outputs.commit()
    return json.dumps(result)

def execute_reference(spec,limit):
    import shutil,signal,subprocess,sys,time
    start=time.time();run=spec['run_id']
    scratch=Path('/work')/run;scratch.mkdir(parents=True,exist_ok=True)
    destination=Path('/persist')/run;destination.mkdir(parents=True,exist_ok=True)
    (scratch/'spec.json').write_text(json.dumps(spec))
    (destination/'started.json').write_text(json.dumps(dict(started_unix=start,run_id=run)))
    outputs.commit()
    def backup():
        folder=scratch/'phase2-output'
        if folder.exists():
            for path in folder.iterdir():
                if path.suffix in ['.jsonl','.csv','.log','.txt','.json']:
                    data=path.read_bytes()
                    if path.suffix in ['.jsonl','.csv'] and data and not data.endswith(b'\n'):
                        data=data[:data.rfind(b'\n')+1]
                    (destination/path.name).write_bytes(data)
        outputs.commit()
    with (scratch/'process.log').open('w') as log:
        child=subprocess.Popen([sys.executable,'/study/adapter.py',str(scratch/'spec.json')],cwd=scratch,
                               stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            if time.time()-start>limit-45:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait()
                break
            backup();time.sleep(20)
        code=child.wait()
    backup();shutil.copyfile(scratch/'process.log',destination/'process.log')
    result=dict(kind='phase3_modal_run',phase='phase3',run_id=run,returncode=code,
                duration_s=time.time()-start,requested_gpu=GPU,container_id=os.environ.get('MODAL_TASK_ID'))
    rows=[json.loads(line) for line in (destination/'results.jsonl').read_text().splitlines()]
    completed={r['model'] for r in rows if r['kind']=='model_complete' and r['completed']}
    result['complete']=code==0 and set(spec['models'])<=completed and not any(r['kind']=='measurement' and not r['valid'] for r in rows)
    (destination/'done.json').write_text(json.dumps(result));outputs.commit()
    return result


def execute_h100(spec):
    import hashlib,time,traceback
    start=time.time();folder=Path('/persist')/spec['run_id'];folder.mkdir(parents=True,exist_ok=True)
    completed=[];success=False;error=None
    try:
        for stage in spec['calibration_stages']:
            outcome=execute_reference(stage,240);completed.append(stage['run_id'])
            assert outcome['complete'],'H100 calibration failed: '+stage['run_id']
        (folder/'ready.json').write_text(json.dumps(dict(started_unix=start,elapsed_s=time.time()-start,
             calibration_run_ids=completed,container_id=os.environ.get('MODAL_TASK_ID'))));outputs.commit()
        deadline=min(time.time()+300,start+LIMIT-1000)
        release=None
        while time.time()<deadline:
            outputs.reload()
            if (folder/'release.json').exists():
                release=json.loads((folder/'release.json').read_text());break
            time.sleep(2)
        assert release is not None,'No committed prediction release before H100 gate deadline'
        assert len(release['prediction_commit'])==40 and all(c in '0123456789abcdef' for c in release['prediction_commit'])
        assert hashlib.sha256(release['manifest_text'].encode()).hexdigest()==release['manifest_sha256']
        manifest=json.loads(release['manifest_text']);assert manifest['gpu']=='H100!' and manifest['calibration_only']
        allowed={r['name']:r for r in spec['planned_runs']}
        stages=release['sweep_stages']
        assert sum(s['_stage_timeout_s'] for s in stages)+time.time()-start+45<LIMIT,'H100 projections do not fit remaining session'
        for stage in stages:
            planned=allowed[stage['run_id'].removeprefix('phase3-')]
            assert stage['models']==planned['models'] and stage['lengths_by_model']==planned['lengths_by_model']
            assert stage['turns_by_model']==planned['turns_by_model'] and stage['workloads']==[planned['workload']]
            assert stage['prediction_commit']==release['prediction_commit']
            outcome=execute_reference(stage,stage['_stage_timeout_s']);completed.append(stage['run_id'])
            assert outcome['complete'],'H100 sweep stage incomplete: '+stage['run_id']
        success=True
    except Exception:
        error=traceback.format_exc()
    result=dict(kind='phase3_modal_run',phase='phase3',run_id=spec['run_id'],duration_s=time.time()-start,
                requested_gpu=GPU,container_id=os.environ.get('MODAL_TASK_ID'),complete=success,
                stage_run_ids=completed,error=error,returncode=0 if success else 1)
    (folder/'done.json').write_text(json.dumps(result));outputs.commit()
    return result


@app.function(image=image,gpu=GPU,cpu=(CPU,CPU),memory=(RAM,RAM),
              volumes={'/cache':cache,'/persist':outputs},timeout=LIMIT,startup_timeout=90,
              scaledown_window=2,max_containers=1,retries=0,single_use_containers=True)
def execute(spec):
    result=execute_h100(spec) if spec['purpose']=='h100_combined' else execute_reference(spec,LIMIT)
    return json.dumps(result)

@app.local_entrypoint()
def main(spec_path: str='',prepare: bool=False):
    if prepare:return preload.remote()
    return execute.remote(json.loads(Path(spec_path).read_text()))
