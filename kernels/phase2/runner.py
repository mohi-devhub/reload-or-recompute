"""Kaggle phase-two reference runner. CONFIG_JSON is injected by the builder."""
import gc
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time
import traceback

CONFIG_JSON = '{}'
SPEC = json.loads(CONFIG_JSON)
ROOT = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
OUT = ROOT / 'phase2-output'
OUT.mkdir(exist_ok=True)
START = time.time()
ENV = {}
MODEL_INFO = {}
CURRENT = {}


def emit(kind, **fields):
    row = dict(schema_version=2, kind=kind, run_id=SPEC['run_id'], phase='phase2',
               timestamp_unix=time.time(), process_elapsed_s=time.time() - START,
               environment=ENV, **MODEL_INFO, **CURRENT)
    row.update(fields)
    with (OUT / 'results.jsonl').open('a') as f:
        f.write(json.dumps(row, allow_nan=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    if kind not in ['measurement', 'microbenchmark']:
        print(json.dumps(row, allow_nan=False), flush=True)


def version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return 'not installed'


def environment():
    global ENV
    smi = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    print(smi.stdout, flush=True)
    import torch
    query = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                            '--format=csv,noheader'], capture_output=True, text=True)
    ENV = dict(gpu_names=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
               gpu_count=torch.cuda.device_count(), gpu_query=query.stdout.strip(),
               torch=torch.__version__, cuda_runtime=torch.version.cuda,
               transformers=version('transformers'), vllm=version('vllm'),
               lmcache=version('lmcache'), python=sys.version.split()[0],
               cpu_count=os.cpu_count(), cpu_ram_kb=int(Path('/proc/meminfo').read_text().splitlines()[0].split()[1]),
               free_working_bytes=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize,
               free_tmp_bytes=os.statvfs('/tmp').f_bavail * os.statvfs('/tmp').f_frsize,
               source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               requested_gpu=SPEC['gpu'])
    print('ENVIRONMENT ' + json.dumps(ENV), flush=True)
    emit('environment', nvidia_smi=smi.stdout, load_average=os.getloadavg(), specification=SPEC)
    expected = 'T4' if SPEC['gpu'] == 'NvidiaTeslaT4' else 'P100'
    if not ENV['gpu_names'] or any(expected not in x for x in ENV['gpu_names']):
        raise RuntimeError('Requested GPU does not match allocation')
    if ENV['gpu_count'] > SPEC.get('max_allocated_gpus', 2):
        raise RuntimeError('Unexpected GPU allocation exceeds reservation')
    torch.cuda.set_device(0)
    return torch


def telemetry():
    base = 'timestamp,index,clocks.sm,clocks.mem,temperature.gpu,power.draw,utilization.gpu'
    for reason in ['clocks_throttle_reasons.active', 'clocks_event_reasons.active']:
        query = base + ',' + reason
        probe = subprocess.run(['nvidia-smi', '--query-gpu=' + query,
                                '--format=csv,noheader,nounits'], capture_output=True, text=True)
        if probe.returncode == 0:
            handle = (OUT / 'telemetry.csv').open('w')
            handle.write(query + '\n')
            handle.flush()
            process = subprocess.Popen(['nvidia-smi', '--query-gpu=' + query,
                                        '--format=csv,noheader,nounits', '--loop-ms=1000'],
                                       stdout=handle, stderr=handle)
            emit('telemetry_started', columns=query, sample_period_s=1,
                 timestamp_basis='nvidia-smi UTC in Kaggle container')
            return process, handle
    emit('telemetry_unavailable', error=probe.stderr)
    return None, None


def read_bytes():
    return int(next(x.split(':')[1] for x in Path('/proc/self/io').read_text().splitlines()
                    if x.startswith('read_bytes:')))


def evict(path):
    with path.open('rb') as f:
        os.fsync(f.fileno())
        try:
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            return 'DONTNEED_advisory'
        except (AttributeError, OSError) as e:
            return type(e).__name__ + ': ' + str(e)


def timed(torch, fn):
    torch.cuda.synchronize()
    begin_event, end_event = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    begin_event.record()
    start_unix, start = time.time(), time.perf_counter()
    value = fn()
    end_event.record()
    torch.cuda.synchronize()
    return value, dict(wall_ms=(time.perf_counter() - start) * 1000,
                       cuda_event_ms=begin_event.elapsed_time(end_event),
                       wall_start_unix=start_unix, wall_end_unix=time.time())


def flat_reload(torch, source, shapes, target_rate):
    """Blocking serialized transport simulation; consume all copied bytes afterward."""
    start = time.perf_counter()
    destination = torch.empty(source.numel(), dtype=source.dtype, device='cuda')
    chunk_elements = SPEC.get('chunk_bytes', 4 * 1024 * 1024) // source.element_size()
    slept = 0.0
    for offset in range(0, source.numel(), chunk_elements):
        count = min(chunk_elements, source.numel() - offset)
        destination[offset:offset + count].copy_(source[offset:offset + count], non_blocking=True)
        if target_rate is not None:
            torch.cuda.current_stream().synchronize()
            deadline = start + (offset + count) * source.element_size() / target_rate
            delay = deadline - time.perf_counter()
            if delay > 0:
                before = time.perf_counter()
                time.sleep(delay)
                slept += time.perf_counter() - before
    torch.cuda.synchronize()
    transfer_ms = (time.perf_counter() - start) * 1000
    flat, offset = [], 0
    for layer in shapes:
        tensors = []
        for shape in layer:
            count = 1
            for n in shape:
                count *= n
            tensors.append(destination[offset:offset + count].view(shape))
            offset += count
        flat.append(tuple(tensors))
    assert offset == source.numel()
    return tuple(flat), dict(transfer_ms=transfer_ms, rate_limiter_sleep_ms=slept * 1000,
                            achieved_transport_bytes_s=source.numel() * source.element_size() * 1000 / transfer_ms,
                            target_bandwidth_bytes_s=target_rate,
                            simulated_bandwidth=True, chunk_bytes=chunk_elements * source.element_size())


def source_tokens(tokenizer, workload, needed):
    if workload == 'repeated_control':
        text = ('User: Explain how a computer stores and retrieves a conversation.\n'
                'Assistant: A conversation consists of messages in order. Each message '
                'adds information that later messages can use.\n')
        ids = tokenizer.encode(text, add_special_tokens=False)
        return (ids * (needed // len(ids) + 2))[:needed], dict(workload=workload)
    rows = SPEC['conversation_data']['rows']
    ids, used = [], []
    for row in rows:
        text = ''.join(m['role'] + ': ' + m['content'] + '\n' for m in row['messages'])
        ids.extend(tokenizer.encode(text, add_special_tokens=False))
        used.append(row['prompt_id'])
        if len(ids) >= needed:
            break
    if len(ids) < needed:
        raise RuntimeError('Frozen conversation fixture has insufficient nonrepeated tokens')
    return ids[:needed], dict(workload=workload, dataset='HuggingFaceH4/ultrachat_200k',
                             conversation_ids=used, stitched_conversations=len(used) > 1,
                             format='plain role-labelled conversation text, token-clipped',
                             fixture_sha256=hashlib.sha256(json.dumps(SPEC['conversation_data'], sort_keys=True).encode()).hexdigest())


def model_run(torch, model_id):
    global MODEL_INFO, CURRENT
    MODEL_INFO, CURRENT = {}, {}
    from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache
    from torch.nn.attention import sdpa_kernel, SDPBackend
    token = None
    if model_id.startswith('meta-llama/'):
        try:
            from kaggle_secrets import UserSecretsClient
            token = UserSecretsClient().get_secret(SPEC.get('hf_secret_label', 'HF_TOKEN'))
        except Exception as e:
            emit('secret_unavailable', model=model_id, error_type=type(e).__name__)
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    model = AutoModelForCausalLM.from_pretrained(model_id, token=token, torch_dtype=torch.float16,
                                                attn_implementation='sdpa').to('cuda').eval()
    cfg = model.config
    heads, layers = cfg.num_attention_heads, cfg.num_hidden_layers
    kvheads = getattr(cfg, 'num_key_value_heads', heads)
    dim = getattr(cfg, 'head_dim', None) or cfg.hidden_size // heads
    bpt = 2 * layers * kvheads * dim * 2
    MODEL_INFO = dict(model=model_id, model_revision=getattr(cfg, '_commit_hash', None),
                      dtype='float16', attention_family='GQA' if kvheads < heads else 'MHA',
                      kv_bytes_per_token=bpt, layers=layers, kv_heads=kvheads, head_dim=dim,
                      concurrency=1)
    emit('model_config', config=cfg.to_dict(), parameter_count=sum(p.numel() for p in model.parameters()),
         supports_cache_class=getattr(model, '_supports_cache_class', False))
    cache_class = getattr(model, '_supports_cache_class', False)
    base, head = model.base_model, model.get_output_embeddings()

    def forward(ids, past=None):
        cache = DynamicCache.from_legacy_cache(past) if past is not None and cache_class else past
        output = base(input_ids=ids, past_key_values=cache, use_cache=True, return_dict=True)
        logits = head(output.last_hidden_state[:, -1, :])
        selected = int(logits.argmax(dim=-1).item())
        return logits, output.past_key_values, selected

    def legacy(cache):
        return cache.to_legacy_cache() if hasattr(cache, 'to_legacy_cache') else cache

    backend = [SDPBackend.EFFICIENT_ATTENTION, SDPBackend.MATH]
    max_context = getattr(cfg, 'max_position_embeddings', 32768)
    lengths = SPEC['lengths'].copy()
    boundary = max_context - max(SPEC['turns'])
    if boundary < max(lengths) and boundary > min(lengths):
        lengths.append(boundary)
    lengths = sorted(set(lengths))
    rng = random.Random(SPEC['seed'])
    rng.shuffle(lengths)
    worksets = SPEC.get('workloads', ['repeated_control'])
    token_sets = {w: source_tokens(tokenizer, w, max(SPEC['lengths']) + max(SPEC['turns']))
                  for w in worksets}
    done = set()
    for line in (OUT / 'results.jsonl').read_text().splitlines():
        try:
            r = json.loads(line)
            if r.get('kind') == 'measurement' and r.get('valid') and r.get('model') == model_id:
                done.add((r['workload'], r['prefix_tokens'], r['turn_tokens'], r['repeat'], r['condition']))
        except json.JSONDecodeError:
            pass
    with torch.inference_mode(), sdpa_kernel(backend):
        warm = torch.tensor([token_sets[worksets[0]][0][:512]], device='cuda')
        deadline = time.monotonic() + SPEC.get('stabilize_s', 10)
        while time.monotonic() < deadline:
            result = forward(warm)
            del result
        emit('stabilized', duration_s=SPEC.get('stabilize_s', 10))
        del warm
        for workload in worksets:
            ids, provenance = token_sets[workload]
            emit('workload', **provenance)
            for length in lengths:
                if length + min(SPEC['turns']) > max_context:
                    emit('shape_skipped', workload=workload, prefix_tokens=length,
                         reason='prefix plus new turn exceeds native model context', max_context=max_context)
                    continue
                CURRENT = dict(workload=workload, prefix_tokens=length)
                prefix = torch.tensor([ids[:length]], device='cuda')
                prefix_result = forward(prefix)
                gpu = tuple(tuple(t.detach() for t in layer) for layer in legacy(prefix_result[1]))
                del prefix_result
                shapes = [[list(t.shape) for t in layer] for layer in gpu]
                pageable = torch.cat([t.cpu().contiguous().view(-1) for layer in gpu for t in layer])
                pinned = pageable.pin_memory()
                payload_bytes = pageable.numel() * pageable.element_size()
                assert payload_bytes == bpt * length
                torch_path, raw_path = OUT / 'cache.pt', OUT / 'cache.bin'
                torch.save(pageable, torch_path)
                with raw_path.open('wb') as f:
                    f.write(pageable.numpy().tobytes())
                    f.flush()
                    os.fsync(f.fileno())
                emit('cache_layout', kv_bytes=payload_bytes, kv_bytes_per_token_tensor=payload_bytes // length,
                     tensor_shapes=shapes, torch_file_bytes=torch_path.stat().st_size,
                     raw_file_bytes=raw_path.stat().st_size)
                # Calibrate file legs independently, then predict held-out TTFT samples.
                for fmt, path in [('torch', torch_path), ('raw', raw_path)]:
                    for repeat in range(SPEC.get('micro_repeats', 10)):
                        eviction = evict(path)
                        before = read_bytes()
                        begin = time.perf_counter()
                        payload = bytearray(path.stat().st_size)
                        with path.open('rb', buffering=0) as f:
                            count = f.readinto(payload)
                        raw_ms = (time.perf_counter() - begin) * 1000
                        assert count == len(payload)
                        physical = read_bytes() - before
                        begin = time.perf_counter()
                        cpu = (torch.load(io.BytesIO(payload), map_location='cpu', weights_only=True)
                               if fmt == 'torch' else torch.frombuffer(payload, dtype=torch.float16))
                        decode_ms = (time.perf_counter() - begin) * 1000
                        assert torch.equal(cpu, pageable)
                        copied, transfer = flat_reload(torch, cpu, shapes, None)
                        transfer['simulated_bandwidth'] = False
                        emit('microbenchmark', condition='file_legs_' + fmt, repeat=repeat,
                             raw_read_ms=raw_ms, deserialize_ms=decode_ms, bytes=len(payload),
                             physical_read_bytes=physical, eviction=eviction, valid=True,
                             **transfer)
                        del payload, cpu, copied
                # Both host-memory layouts are calibrated without a new turn.
                for tier, source in [('pinned', pinned), ('pageable', pageable)]:
                    for repeat in range(SPEC.get('micro_repeats', 10)):
                        copied, transfer = flat_reload(torch, source, shapes, None)
                        assert all(torch.equal(a, b) for la, lb in zip(copied, gpu) for a, b in zip(la, lb))
                        transfer['simulated_bandwidth'] = False
                        emit('microbenchmark', condition='h2d_' + tier, repeat=repeat, valid=True,
                             bytes=payload_bytes, **transfer)
                        del copied
                turns = SPEC['turns'].copy()
                rng.shuffle(turns)
                for turn_length in turns:
                    if length + turn_length > max_context:
                        emit('shape_skipped', turn_tokens=turn_length, reason='native_context', max_context=max_context)
                        continue
                    CURRENT['turn_tokens'] = turn_length
                    turn = torch.tensor([ids[length:length + turn_length]], device='cuda')
                    full = torch.cat([prefix, turn], dim=1)
                    baseline = forward(full)
                    target, target_token = baseline[0].float().cpu(), baseline[2]
                    if SPEC['purpose'] == 'calibration' and length == min(SPEC['lengths']):
                        full_cache = legacy(baseline[1])
                        layer_errors = []
                        for old_layer, new_layer in zip(gpu, full_cache):
                            old = torch.cat([t.float().reshape(-1) for t in old_layer])
                            new = torch.cat([t[..., :length, :].float().reshape(-1) for t in new_layer])
                            layer_errors.append(float((old-new).norm()/new.norm()))
                        emit('cache_shape_numerics', relative_l2_by_layer=layer_errors,
                             interpretation='standalone prefix KV versus same prefix inside full fp16 prefill')
                    del baseline
                    resident = forward(turn, gpu)
                    resident_target, resident_token = resident[0].float().cpu(), resident[2]
                    emit('reference_numerics', recompute_token=target_token, resident_token=resident_token,
                         first_token_equal=resident_token == target_token,
                         full_vs_resident_max_abs=float((resident_target-target).abs().max()),
                         full_vs_resident_relative_l2=float((resident_target-target).norm()/target.norm()),
                         policy='restores compared with independent resident continuation; full-prefill differences retained')
                    del resident
                    rates = SPEC['rates_mb_s']
                    conditions = ['prefix_only', 'recompute', 'gpu_hit', 'cpu_pageable',
                                  'file_torch_direct', 'file_torch_staged', 'file_raw_staged']
                    conditions += ['simulated_' + str(rate) + '_MBps' for rate in rates]
                    conditions += ['simulated_unthrottled']

                    def request(condition):
                        details = {}
                        if condition == 'prefix_only':
                            return forward(prefix), details
                        if condition == 'recompute':
                            return forward(full), details
                        if condition == 'gpu_hit':
                            return forward(turn, gpu), details
                        source = pinned
                        rate = None
                        if condition.startswith('simulated_') and condition != 'simulated_unthrottled':
                            rate = float(condition.split('_')[1]) * 1e6
                        if condition == 'cpu_pageable':
                            source = pageable
                        elif condition.startswith('file_'):
                            fmt = 'torch' if 'torch' in condition else 'raw'
                            path = torch_path if fmt == 'torch' else raw_path
                            before = read_bytes()
                            start = time.perf_counter()
                            if condition == 'file_torch_direct':
                                source = torch.load(path, map_location='cpu', weights_only=True)
                                details['direct_torch_load_ms'] = (time.perf_counter() - start) * 1000
                            else:
                                payload = bytearray(path.stat().st_size)
                                with path.open('rb', buffering=0) as f:
                                    count = f.readinto(payload)
                                assert count == len(payload)
                                details['raw_read_ms'] = (time.perf_counter() - start) * 1000
                                start = time.perf_counter()
                                source = (torch.load(io.BytesIO(payload), map_location='cpu', weights_only=True)
                                          if fmt == 'torch' else torch.frombuffer(payload, dtype=torch.float16))
                                details['deserialize_ms'] = (time.perf_counter() - start) * 1000
                            details['physical_read_bytes'] = read_bytes() - before
                            details['file_bytes'] = path.stat().st_size
                        cache, transfer = flat_reload(torch, source, shapes, rate)
                        transfer['simulated_bandwidth'] = condition.startswith('simulated_')
                        details.update(transfer)
                        return forward(turn, cache), details

                    for repeat in range(-SPEC['warmups'], SPEC['repeats']):
                        order = conditions.copy()
                        rng.shuffle(order)
                        for position, condition in enumerate(order):
                            if (workload, length, turn_length, repeat, condition) in done:
                                continue
                            if time.time() - START > SPEC['worker_limit_s'] - max(30, payload_bytes / 50e6 + 5):
                                emit('budget_stop', completed=False)
                                return False
                            if condition.startswith('file_'):
                                evict(torch_path if 'torch' in condition else raw_path)
                            torch.cuda.reset_peak_memory_stats()
                            (result, details), timing = timed(torch, lambda: request(condition))
                            logits = result[0].float().cpu()
                            cache_length = (result[1].get_seq_length() if hasattr(result[1], 'get_seq_length')
                                            else result[1][0][0].shape[-2])
                            if condition == 'prefix_only':
                                valid = bool(torch.isfinite(logits).all() and cache_length == length)
                                max_abs, rel_l2, token_equal = None, None, None
                            else:
                                max_abs = (logits - target).abs().max().item()
                                rel_l2 = ((logits - target).norm() / target.norm()).item()
                                token_equal = result[2] == target_token
                                expected = target if condition == 'recompute' else resident_target
                                restore_error = float((logits-expected).abs().max())
                                valid = bool(torch.isfinite(logits).all() and token_equal and
                                             torch.allclose(logits, expected, rtol=0.001, atol=0.001)
                                             and cache_length == length + turn_length)
                            assert all(t.shape[-2] == length for layer in gpu for t in layer)
                            if repeat >= 0 or not valid:
                                emit('measurement', condition=condition, repeat=repeat,
                                     condition_position=position, kv_bytes=payload_bytes,
                                     simulated_bandwidth=condition.startswith('simulated_'),
                                     valid=valid, first_token=result[2], recompute_first_token=target_token,
                                     first_token_equal=token_equal, logits_max_abs=max_abs,
                                     logits_relative_l2=rel_l2, cache_length=cache_length,
                                     restore_logits_max_abs=None if condition=='prefix_only' else restore_error,
                                     peak_vram_bytes=torch.cuda.max_memory_allocated(),
                                     **timing, **{k:v for k,v in details.items() if k != 'simulated_bandwidth'})
                            del result, logits
                            if not valid:
                                raise RuntimeError('Cache correctness failure: ' + condition)
                    emit('shape_complete', repeats=SPEC['repeats'], conditions=conditions)
                    del turn, full, target, resident_target
                del prefix, gpu, pageable, pinned
                torch_path.unlink()
                raw_path.unlink()
                CURRENT = {}
                gc.collect()
                torch.cuda.empty_cache()
        if SPEC.get('anomaly_profile') and model_id == 'Qwen/Qwen2.5-1.5B':
            ids, _ = source_tokens(tokenizer, 'repeated_control', 8448)
            candidates = [(length, torch.tensor([ids[:length]], device='cuda'))
                          for length in [8192, 8224, 8448]]
            for _, value in candidates:
                for _ in range(2):
                    temporary = forward(value)
                    del temporary
            with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                                   torch.profiler.ProfilerActivity.CUDA],
                                        record_shapes=True) as profile:
                for length, value in candidates:
                    with torch.profiler.record_function('shape_' + str(length)):
                        temporary = forward(value)
                        torch.cuda.synchronize()
                        del temporary
            profile.export_chrome_trace(str(OUT / 'anomaly-trace.json'))
            (OUT / 'anomaly-profile.txt').write_text(profile.key_averages(group_by_input_shape=True).table(
                sort_by='self_device_time_total', row_limit=50))
            emit('anomaly_profile_complete', lengths=[8192, 8224, 8448],
                 excluded_from_timings=True, record_shapes=True)
            del candidates
    del model, base, head
    gc.collect()
    torch.cuda.empty_cache()
    emit('model_complete', completed=True)
    MODEL_INFO, CURRENT = {}, {}
    return True


def worker(torch):
    torch.set_num_threads(min(4, os.cpu_count()))
    torch.manual_seed(SPEC['seed'])
    for model in SPEC['models']:
        try:
            if not model_run(torch, model):
                return
        except Exception:
            emit('model_failed', model=model, error=traceback.format_exc(), completed=False)
            if not SPEC.get('continue_on_model_error', False):
                raise
            gc.collect()
            torch.cuda.empty_cache()
    emit('run_complete', completed=True)


def main():
    if '--worker-limit-s' in sys.argv:
        SPEC['worker_limit_s']=int(sys.argv[sys.argv.index('--worker-limit-s')+1])
    torch = environment()
    if '--worker' in sys.argv:
        worker(torch)
        return
    monitor, handle = telemetry()
    try:
        with (OUT / 'install.log').open('w') as log:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                                     'transformers==4.51.3', 'safetensors', 'accelerate'],
                                    stdout=log, stderr=subprocess.STDOUT, timeout=300)
        if result.returncode:
            raise RuntimeError('Reference installation failed')
        deadline=SPEC.get('session_limit_s')
        remaining=int(deadline-(time.time()-START)) if deadline is not None else SPEC['worker_limit_s']
        worker_limit=min(SPEC['worker_limit_s'],remaining)
        if worker_limit<=30:
            raise RuntimeError('Setup exhausted the session deadline; no benchmark worker started')
        emit('worker_budget',worker_limit_s=worker_limit,setup_elapsed_s=time.time()-START,
             session_limit_s=SPEC.get('session_limit_s'))
        with (OUT / 'worker.log').open('w') as log:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker',
                                      '--worker-limit-s',str(worker_limit)],
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = child.wait(timeout=worker_limit)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                code = 124
        emit('worker_status', returncode=code)
    except Exception:
        emit('fatal_error', error=traceback.format_exc())
        raise
    finally:
        if monitor:
            monitor.terminate()
            monitor.wait(timeout=5)
            handle.close()
        elapsed = time.time() - START
        emit('allocation_end', duration_s=elapsed,
             conservative_gpu_hours=elapsed * ENV['gpu_count'] / 3600)


if __name__ == '__main__':
    main()
