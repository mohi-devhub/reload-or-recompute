"""Private Kaggle pilot. No credentials are required inside this kernel."""
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
OUT = ROOT / 'pilot-output'
OUT.mkdir(exist_ok=True)
RESULTS = OUT / 'results.jsonl'
MODEL = 'Qwen/Qwen2.5-1.5B'
PREFIXES = [512, 2048, 8192]
TURNS = [32, 256]
REPEATS = 12
WARMUPS = 2
SEED = 7321
START = time.time()
RUN_ID = os.environ.get('ROR_RUN_ID', 'pilot-t4-v1')
PRODUCTION_ONLY = False
ENV = {}


def emit(kind, **fields):
    row = dict(schema_version=1, run_id=RUN_ID, kind=kind,
               timestamp_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               elapsed_s=time.time() - START, environment=ENV, **fields)
    with RESULTS.open('a') as f:
        f.write(json.dumps(row, allow_nan=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps(row, allow_nan=False), flush=True)


def version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return 'not installed'


def command(args, timeout=60):
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return dict(command=args, returncode=p.returncode, output=p.stdout)


def environment():
    global ENV
    # This is deliberately the first command and output in every process log.
    smi = command(['nvidia-smi'])
    print(smi['output'], flush=True)
    import torch
    info = command(['nvidia-smi', '--query-gpu=name,driver_version,memory.total,uuid',
                    '--format=csv,noheader'])
    ENV = dict(nvidia_smi=smi, gpu_query=info,
               cuda_runtime=torch.version.cuda, torch=torch.__version__,
               vllm=version('vllm'), lmcache=version('lmcache'),
               transformers=version('transformers'), python=sys.version,
               cpu_count=os.cpu_count(), load_average=os.getloadavg(),
               cpu_ram=Path('/proc/meminfo').read_text(),
               free_disk_bytes={str(p): shutil.disk_usage(p).free
                                for p in [ROOT, Path('/tmp')]},
               gpu_count=torch.cuda.device_count(),
               gpus=[dict(name=torch.cuda.get_device_name(i),
                          capability=torch.cuda.get_device_capability(i),
                          total_memory=torch.cuda.get_device_properties(i).total_memory)
                     for i in range(torch.cuda.device_count())],
               requested_gpu='NvidiaTeslaT4',
               source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    print('ENVIRONMENT ' + json.dumps(ENV), flush=True)
    emit('environment')
    if not ENV['gpus'] or any('T4' not in g['name'] for g in ENV['gpus']):
        raise RuntimeError('Requested T4, observed different GPU: refusing benchmark')
    if ENV['gpu_count'] > 2:
        raise RuntimeError('Unexpected allocation exceeds pilot budget assumptions')
    torch.cuda.set_device(0)
    return torch


def io_read_bytes():
    data = Path('/proc/self/io').read_text().splitlines()
    return int(next(s.split(':')[1] for s in data if s.startswith('read_bytes:')))


def evict(path):
    # fsync before DONTNEED: dirty pages would otherwise remain resident.
    with open(path, 'rb') as f:
        os.fsync(f.fileno())
        try:
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            return 'posix_fadvise_DONTNEED_hint_only'
        except (AttributeError, OSError) as e:
            return type(e).__name__ + ': ' + str(e)


def timed(torch, fn):
    torch.cuda.synchronize()
    a, b = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    a.record()
    wall = time.perf_counter()
    value = fn()
    b.record()
    torch.cuda.synchronize()
    elapsed = (time.perf_counter() - wall) * 1000
    cuda = a.elapsed_time(b)
    return value, elapsed, cuda


def existing_keys():
    if not RESULTS.exists():
        return set()
    keys = set()
    for line in RESULTS.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get('kind') in ['ttft', 'prefill', 'bandwidth'] and r.get('valid', True):
            keys.add((r['kind'], r.get('prefix_tokens'), r.get('turn_tokens'),
                      r.get('condition'), r['repeat']))
    return keys


def reference(torch):
    from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache
    from torch.nn.attention import sdpa_kernel, SDPBackend
    torch.manual_seed(SEED)
    random.seed(SEED)
    torch.set_num_threads(min(4, os.cpu_count()))
    emit('protocol', model=MODEL, prefix_lengths=PREFIXES, new_turn_lengths=TURNS,
         repeats=REPEATS, warmups=WARMUPS, concurrency=1, dtype='float16',
         attention='torch SDPA efficient or math; flash backend disabled',
         ttft_boundary='GPU input IDs ready through first token selected and copied to CPU',
         excluded='tokenization, prefix cache creation, offload writes, queueing, network',
         bootstrap_seed=SEED, bootstrap_resamples=10000,
         model_seed=SEED, checkpoint_resumption='valid sample keys in results.jsonl')
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.float16, attn_implementation='sdpa').to('cuda').eval()
    cfg = model.config
    head_dim = getattr(cfg, 'head_dim', None) or cfg.hidden_size // cfg.num_attention_heads
    bpt = 2 * cfg.num_hidden_layers * cfg.num_key_value_heads * head_dim * 2
    emit('model_config', model=MODEL, config=cfg.to_dict(),
         model_revision=getattr(cfg, '_commit_hash', None),
         kv_bytes_per_token_config=bpt, tokenizer_class=type(tokenizer).__name__)
    text = ('User: Explain how a computer stores and retrieves a conversation.\n'
            'Assistant: A conversation consists of messages in order. Each message '
            'adds information that later messages can use.\n')
    base = tokenizer.encode(text, add_special_tokens=False)
    all_ids = (base * ((max(PREFIXES) + max(TURNS)) // len(base) + 2))
    done = existing_keys()

    def forward(ids, past=None):
        cache = DynamicCache.from_legacy_cache(past) if past is not None else None
        output = model.model(input_ids=ids, past_key_values=cache,
                             use_cache=True, return_dict=True)
        logits = model.lm_head(output.last_hidden_state[:, -1, :])
        token = int(logits.argmax(dim=-1).item())
        return logits, output.past_key_values, token

    try:
        with open('/proc/sys/vm/drop_caches', 'w') as f:
            f.write('3\n')
        drop_status = 'global drop_caches succeeded once; per-file hint before samples'
    except OSError as e:
        drop_status = f'{type(e).__name__}: {e}'
    emit('disk_cache_control', global_drop_caches=drop_status,
         policy='fsync and DONTNEED before file samples; physical read_bytes recorded',
         warning='DONTNEED is advisory, not proof of cold disk; virtual storage unspecified')

    with torch.inference_mode(), sdpa_kernel([SDPBackend.EFFICIENT_ATTENTION, SDPBackend.MATH]):
        for length in PREFIXES:
            prefix = torch.tensor([all_ids[:length]], device='cuda')
            # Warm the prefix shape, then measure prefix-only recompute directly.
            for _ in range(WARMUPS):
                temp = forward(prefix)
                del temp
            for repeat in range(REPEATS):
                key = ('prefill', length, None, 'prefix_only', repeat)
                if key in done:
                    continue
                result, wall, cuda = timed(torch, lambda: forward(prefix))
                emit('prefill', model=MODEL, prefix_tokens=length,
                     condition='prefix_only', repeat=repeat, wall_ms=wall,
                     cuda_ms=cuda, tokens_per_s=length / (wall / 1000), valid=True)
                del result
            temp = forward(prefix)
            gpu = tuple(tuple(t.detach() for t in layer) for layer in temp[1].to_legacy_cache())
            del temp
            shapes = [[list(t.shape) for t in layer] for layer in gpu]
            cache_bytes = sum(t.numel() * t.element_size() for layer in gpu for t in layer)
            assert cache_bytes == bpt * length, (cache_bytes, bpt, length)
            pageable = tuple(tuple(t.cpu().contiguous() for t in layer) for layer in gpu)
            pinned = tuple(tuple(t.pin_memory() for t in layer) for layer in pageable)
            assert all(t.is_pinned() for layer in pinned for t in layer)
            assert all(not t.is_pinned() for layer in pageable for t in layer)
            path = OUT / f'kv-{length}.pt'
            torch.save(pageable, path)
            with path.open('rb') as f:
                os.fsync(f.fileno())
            emit('cache_layout', model=MODEL, prefix_tokens=length,
                 tensor_shapes=shapes, kv_bytes=cache_bytes,
                 kv_bytes_per_token_tensor=cache_bytes // length,
                 kv_bytes_per_token_config=bpt, file_bytes=path.stat().st_size)

            def load_cpu(source):
                return tuple(tuple(t.to('cuda', non_blocking=True) for t in layer)
                             for layer in source)

            # Use the same tensor layout and allocations as the actual reload.
            for tier, source in [('pinned', pinned), ('pageable', pageable)]:
                for repeat in range(-WARMUPS, REPEATS):
                    key = ('bandwidth', length, None, 'h2d_' + tier, repeat)
                    if key in done:
                        continue
                    copied, wall, cuda = timed(torch, lambda: load_cpu(source))
                    if repeat >= 0:
                        assert all(torch.equal(a, b) for la, lb in zip(copied, gpu)
                                   for a, b in zip(la, lb))
                        emit('bandwidth', prefix_tokens=length, repeat=repeat,
                             condition='h2d_' + tier, bytes=cache_bytes,
                             wall_ms=wall, cuda_ms=cuda,
                             bytes_per_s=cache_bytes / (wall / 1000), valid=True)
                    del copied
            # Independent raw file-read benchmark, without torch deserialization.
            for repeat in range(REPEATS):
                key = ('bandwidth', length, None, 'file_read', repeat)
                if key in done:
                    continue
                eviction = evict(path)
                before = io_read_bytes()
                begin = time.perf_counter()
                with path.open('rb', buffering=0) as f:
                    payload = f.read()
                wall = (time.perf_counter() - begin) * 1000
                assert len(payload) == path.stat().st_size
                emit('bandwidth', prefix_tokens=length, repeat=repeat, condition='file_read',
                     bytes=len(payload), wall_ms=wall,
                     bytes_per_s=len(payload) / (wall / 1000),
                     physical_read_bytes=io_read_bytes() - before,
                     eviction=eviction, valid=True)
                del payload

            for turn_length in TURNS:
                turn = torch.tensor([all_ids[length:length + turn_length]], device='cuda')
                full = torch.cat([prefix, turn], dim=1)
                full_result = forward(full)
                target = full_result[0].detach().float().cpu()
                target_token = full_result[2]
                del full_result
                conditions = ['recompute', 'cpu_pinned', 'cpu_pageable', 'file', 'gpu_hit']

                def request(condition):
                    if condition == 'recompute':
                        return forward(full)
                    if condition == 'gpu_hit':
                        return forward(turn, gpu)
                    source = pinned if condition == 'cpu_pinned' else pageable
                    if condition == 'file':
                        source = torch.load(path, map_location='cpu', weights_only=True)
                    return forward(turn, load_cpu(source))

                for repeat in range(-WARMUPS, REPEATS):
                    order = conditions.copy()
                    random.Random(SEED + length + turn_length + repeat).shuffle(order)
                    for condition in order:
                        key = ('ttft', length, turn_length, condition, repeat)
                        if key in done:
                            continue
                        eviction = evict(path) if condition == 'file' else None
                        before = io_read_bytes()
                        torch.cuda.reset_peak_memory_stats()
                        result, wall, cuda = timed(torch, lambda: request(condition))
                        read_bytes = io_read_bytes() - before
                        logits = result[0].float().cpu()
                        max_abs = (logits - target).abs().max().item()
                        rel_l2 = ((logits - target).norm() / target.norm()).item()
                        token_equal = result[2] == target_token
                        cache_length = result[1].get_seq_length()
                        valid = bool(torch.isfinite(logits).all() and
                                     torch.allclose(logits, target, rtol=0.02, atol=0.05)
                                     and token_equal and cache_length == length + turn_length)
                        assert all(t.shape[-2] == length for layer in gpu for t in layer)
                        if repeat >= 0:
                            emit('ttft', model=MODEL, prefix_tokens=length,
                                 turn_tokens=turn_length, condition=condition, repeat=repeat,
                                 concurrency=1, dtype='float16', kv_bytes=cache_bytes,
                                 kv_bytes_per_token=bpt, wall_ms=wall, cuda_ms=cuda,
                                 physical_read_bytes=read_bytes, eviction=eviction,
                                 first_token=result[2], recompute_token=target_token,
                                 first_token_equal=token_equal, logits_max_abs=max_abs,
                                 logits_relative_l2=rel_l2, cache_length=cache_length,
                                 valid=valid, peak_vram_bytes=torch.cuda.max_memory_allocated(),
                                 load_average=os.getloadavg())
                        if not valid:
                            raise RuntimeError(f'Correctness check failed: {length}, '
                                               f'{turn_length}, {condition}, {max_abs}, {rel_l2}')
                        del result, logits
                # An unreported profile gives kernel evidence for the limiter.
                if length == 2048 and turn_length == 32:
                    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                                           torch.profiler.ProfilerActivity.CUDA]) as p:
                        for condition in conditions:
                            with torch.profiler.record_function(condition):
                                prof_result = request(condition)
                                torch.cuda.synchronize()
                                del prof_result
                    p.export_chrome_trace(str(OUT / 'reference-trace.json'))
                    (OUT / 'profile.txt').write_text(p.key_averages().table(
                        sort_by='self_device_time_total', row_limit=40))
            del gpu, pageable, pinned, prefix, turn, full
            path.unlink()  # KV data are temporary, never downloaded as results.
            gc.collect()
            torch.cuda.empty_cache()
    emit('reference_complete', valid=True)


def bounded(args, name, seconds, env=None):
    begin = time.monotonic()
    with (OUT / f'{name}.log').open('w') as log:
        child = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, env=env)
        try:
            code = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
    elapsed = time.monotonic() - begin
    emit('subprocess', name=name, command=args, returncode=code,
         duration_s=elapsed, gpu_count=ENV['gpu_count'],
         allocated_gpu_hours=elapsed * ENV['gpu_count'] / 3600)
    return code, elapsed


def production():
    # One isolated, bounded attempt. Do not disturb reference dependencies.
    begin = time.monotonic()
    max_seconds = min(1200, int(2700 / ENV['gpu_count']) - 30)
    py = Path('/tmp/ror-production-venv') / 'bin' / 'python'
    code, _ = bounded([sys.executable, '-m', 'venv', '--without-pip', str(py.parent.parent)],
                      'production-venv', 45)
    if code:
        elapsed = time.monotonic() - begin
        emit('production_status', status='failed_venv', valid=False, returncode=code,
             duration_s=elapsed, allocated_gpu_hours=elapsed * ENV['gpu_count'] / 3600)
        return
    code, _ = bounded([sys.executable, '-m', 'pip', '--python', str(py),
                       'install', '--disable-pip-version-check',
                       'vllm==0.9.0', 'lmcache==0.3.0'],
                      'production-install', max_seconds - 180,
                      dict(os.environ, TORCH_CUDA_ARCH_LIST='7.5', MAX_JOBS='2'))
    if not code:
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', VLLM_USE_V1='0',
                   VLLM_ATTENTION_BACKEND='XFORMERS', LMCACHE_TRACK_USAGE='false',
                   LMCACHE_CHUNK_SIZE='256', LMCACHE_LOCAL_CPU='true',
                   LMCACHE_MAX_LOCAL_CPU_SIZE='2.0',
                   LMCACHE_LOCAL_DISK='file:///kaggle/working/lmcache-disk',
                   LMCACHE_MAX_LOCAL_DISK_SIZE='2.0')
        code, _ = bounded([str(py), str(Path(__file__).resolve()), '--production-child'],
                          'production-runtime', max(30, int(max_seconds - (time.monotonic() - begin))), env)
    emit('production_status', status='failed' if code else 'smoke_completed',
         returncode=code, duration_s=time.monotonic() - begin,
         allocated_gpu_hours=(time.monotonic() - begin) * ENV['gpu_count'] / 3600,
         valid=code == 0,
         scope='compatibility smoke only; no performance conclusion without verified external hits')


def production_child():
    environment()
    from vllm import LLM, SamplingParams
    from vllm.config import KVTransferConfig
    # The historical connector is deliberately version-pinned for Turing support.
    engine = LLM(model=MODEL, dtype='half', max_model_len=9000,
                 enforce_eager=True, gpu_memory_utilization=0.8,
                 enable_prefix_caching=False,
                 kv_transfer_config=KVTransferConfig(kv_connector='LMCacheConnector',
                                                    kv_role='kv_both'))
    text = 'Explain computer memory and conversation history. ' * 256
    for i in range(2):
        output = engine.generate([text], SamplingParams(max_tokens=1, temperature=0))
        emit('production_smoke', iteration=i,
             generated_tokens=output[0].outputs[0].token_ids,
             warning='CPU and disk configured; external-hit counters still require inspection')


def main():
    torch = environment()
    if PRODUCTION_ONLY:
        production()
        elapsed = time.time() - START
        emit('allocation_end', duration_s=elapsed, gpu_count=ENV['gpu_count'],
             allocated_gpu_hours=elapsed * ENV['gpu_count'] / 3600,
             reference_success=None, phase='production_only')
        return
    if '--reference-child' in sys.argv:
        reference(torch)
        return
    # Reference child uses the same installed torch, an explicit transformers version.
    code, _ = bounded([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                       'transformers==4.51.3', 'safetensors', 'accelerate'],
                      'reference-install', 450)
    if code:
        raise RuntimeError('Reference dependency install failed; inspect reference-install.log')
    code, _ = bounded([sys.executable, str(Path(__file__).resolve()), '--reference-child'],
                      'reference', 2400)
    if code:
        emit('reference_failed', returncode=code, valid=False)
    del torch
    gc.collect()
    production()
    elapsed = time.time() - START
    emit('allocation_end', duration_s=elapsed, gpu_count=ENV['gpu_count'],
         allocated_gpu_hours=elapsed * ENV['gpu_count'] / 3600,
         reference_success=code == 0)


if __name__ == '__main__':
    try:
        if '--production-child' in sys.argv:
            production_child()
        else:
            main()
    except Exception:
        error = traceback.format_exc()
        emit('fatal_error', error=error, valid=False)
        raise
