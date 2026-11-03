"""Bounded Modal jobs; the reference measurement functions live in phase two."""
import json
import os
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parents[2]
GPU=os.environ.get('PHASE3_GPU','L4')
LIMIT=int(os.environ.get('PHASE3_TIMEOUT','600'))
NAME=os.environ.get('PHASE3_RUN_NAME','reload-recompute-phase3')
CACHE_NAME='reload-recompute-phase3-models-20261103'
OUTPUT_NAME='reload-recompute-phase3-results-20261103'
cache=modal.Volume.from_name(CACHE_NAME,create_if_missing=True)
outputs=modal.Volume.from_name(OUTPUT_NAME,create_if_missing=True)
image=(modal.Image.debian_slim(python_version='3.13')
       .pip_install('torch==2.11.0+cu130',index_url='https://download.pytorch.org/whl/cu130')
       .pip_install('transformers==4.51.3','safetensors','accelerate','numpy==2.4.6')
       .env({'HF_HOME':'/cache/hf','HF_HUB_DISABLE_PROGRESS_BARS':'1','HF_HUB_DISABLE_TELEMETRY':'1',
             'PHASE3_GPU':GPU,'PHASE3_TIMEOUT':str(LIMIT),'PHASE3_RUN_NAME':NAME})
       .add_local_file(ROOT/'kernels/phase2/runner.py','/study/reference.py')
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

@app.function(image=image,gpu=GPU,cpu=(4,4),memory=(32768,32768),
              volumes={'/cache':cache,'/persist':outputs},timeout=LIMIT,startup_timeout=90,
              scaledown_window=2,max_containers=1,retries=0,single_use_containers=True)
def execute(spec):
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
            if time.time()-start>LIMIT-45:
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
    (destination/'done.json').write_text(json.dumps(result));outputs.commit()
    return json.dumps(result)

@app.local_entrypoint()
def main(spec_path: str='',prepare: bool=False):
    if prepare:return preload.remote()
    return execute.remote(json.loads(Path(spec_path).read_text()))
