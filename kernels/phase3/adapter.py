"""Platform-only entry point around the unchanged phase-two timing path."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from provenance import adapt,functions

spec=json.loads(Path(sys.argv[1]).read_text())
reference=Path('/study/reference.py').read_text()
source=adapt(reference).replace("CONFIG_JSON = '{}'",'CONFIG_JSON = '+repr(json.dumps(spec)))
assert functions(source)==spec['protected_function_hashes']
n={'__name__':'phase2_reference','__file__':'/study/reference.py'}
exec(compile(source,'/study/reference.py','exec'),n)
out=n['OUT']

def emit(kind,**fields):
    row=dict(schema_version=3,kind=kind,run_id=spec['run_id'],phase='phase3',
             timestamp_unix=time.time(),process_elapsed_s=time.time()-n['START'],
             environment=n['ENV'],**n['MODEL_INFO'],**n['CURRENT'])
    row.update(fields)
    with (out/'results.jsonl').open('a') as f:
        f.write(json.dumps(row,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
    if kind not in ['measurement','microbenchmark']:
        print(json.dumps({k:row[k] for k in ['kind','run_id','process_elapsed_s']}),flush=True)


def environment():
    smi=subprocess.run(['nvidia-smi'],capture_output=True,text=True)
    print(smi.stdout,flush=True)
    import torch
    query=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,uuid,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max',
                          '--format=csv,noheader'],capture_output=True,text=True)
    full=subprocess.run(['nvidia-smi','-q'],capture_output=True,text=True)
    (out/'nvidia-smi-q.txt').write_text(full.stdout+full.stderr)
    def version(name):
        try:return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:return 'not installed'
    root=Path.cwd()
    env=dict(gpu_names=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
             gpu_count=torch.cuda.device_count(),gpu_query=query.stdout.strip(),gpu_query_error=query.stderr.strip(),
             compute_capability=list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
             torch=torch.__version__,torch_git_version=torch.version.git_version,cuda_runtime=torch.version.cuda,
             cudnn_version=torch.backends.cudnn.version(),transformers=version('transformers'),vllm=version('vllm'),
             lmcache=version('lmcache'),python=sys.version.split()[0],cpu_count=os.cpu_count(),
             cpu_ram_kb=int(Path('/proc/meminfo').read_text().splitlines()[0].split()[1]),
             cgroup_memory_max=Path('/sys/fs/cgroup/memory.max').read_text().strip() if Path('/sys/fs/cgroup/memory.max').exists() else None,
             cpu_requested_physical=spec.get('platform_cpu',4),memory_requested_gib=spec.get('platform_memory_mib',32768)/1024,
             free_working_bytes=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize,
             free_tmp_bytes=os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize,
             source_sha256=hashlib.sha256(source.encode()).hexdigest(),requested_gpu=spec['gpu'],platform='Modal')
    n['ENV']=env
    print('ENVIRONMENT '+json.dumps(env),flush=True)
    emit('environment',nvidia_smi=smi.stdout,load_average=os.getloadavg(),specification=spec,
         filesystem=subprocess.run(['df','-T',str(root),'/tmp'],capture_output=True,text=True).stdout)
    emit('source_provenance',reference_source_sha256=hashlib.sha256(reference.encode()).hexdigest(),
         executed_source_sha256=env['source_sha256'],adapter_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         protected_function_hashes=functions(source),protected_functions_match_t4=True)
    expected={'L4':(8,9),'A10':(8,6),'H100!':(9,0)}[spec['gpu']]
    assert env['gpu_count']==1,'Unexpected GPU count'
    assert tuple(env['compute_capability'])==expected,'Unexpected compute capability'
    assert ('A10' if spec['gpu']=='A10' else spec['gpu'].rstrip('!')) in env['gpu_names'][0],'GPU allocation mismatch'
    assert env['torch']=='2.11.0+cu130' and env['transformers']=='4.51.3','Pinned runtime mismatch'
    torch.cuda.set_device(0)
    return torch


def telemetry():
    base='timestamp,index,clocks.sm,clocks.mem,temperature.gpu,power.draw,utilization.gpu'
    pcie=',pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max'
    for extra in [pcie,'']:
        for reason in ['clocks_throttle_reasons.active','clocks_event_reasons.active']:
            query=base+','+reason+extra
            probe=subprocess.run(['nvidia-smi','--query-gpu='+query,'--format=csv,noheader,nounits'],capture_output=True,text=True)
            if probe.returncode==0:
                handle=(out/'telemetry.csv').open('w');handle.write(query+'\n');handle.flush()
                process=subprocess.Popen(['nvidia-smi','--query-gpu='+query,'--format=csv,noheader,nounits','--loop-ms=1000'],stdout=handle,stderr=handle)
                emit('telemetry_started',columns=query,sample_period_s=1,pcie_in_continuous_log=bool(extra))
                return process,handle
    emit('telemetry_unavailable',error=probe.stderr)
    return None,None


def direct_micro(torch,path,pageable,shapes):
    for repeat in range(spec['micro_repeats']):
        eviction=n['evict'](path);before=n['read_bytes']();begin=time.perf_counter()
        cpu=torch.load(path,map_location='cpu',weights_only=True)
        load=(time.perf_counter()-begin)*1000;physical=n['read_bytes']()-before
        assert torch.equal(cpu,pageable)
        copied,transfer=n['flat_reload'](torch,cpu,shapes,None)
        emit('microbenchmark',condition='file_legs_direct',repeat=repeat,bytes=path.stat().st_size,
             direct_load_ms=load,physical_read_bytes=physical,eviction=eviction,valid=True,
             **{**transfer,'simulated_bandwidth':False})
        del cpu,copied

n.update(emit=emit,environment=environment,telemetry=telemetry,direct_micro=direct_micro)
monitor=handle=None
try:
    torch=environment();monitor,handle=telemetry()
    n['worker'](torch)
except Exception:
    emit('fatal_error',error=traceback.format_exc());raise
finally:
    if monitor:
        monitor.terminate();monitor.wait(timeout=5);handle.close()
    emit('allocation_end',duration_s=time.time()-n['START'])
