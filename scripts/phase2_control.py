"""Submit, account for, and retrieve private redesigned Kaggle experiments."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'outputs/phase2_ledger.json'
RAW = ROOT / 'outputs/raw/phase2'
GENERATED = ROOT / 'kernels/phase2/generated'
DEFAULT_MODELS = ['Qwen/Qwen2.5-0.5B', 'Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B',
                  'unsloth/Llama-3.2-3B-Instruct', 'EleutherAI/pythia-1.4b',
                  'facebook/opt-1.3b', 'microsoft/phi-2']
FULL_LENGTHS = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]


def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else dict(
        phase2_limit_gpu_hours=10, runs=[], full_grid='redesigned_bandwidth_grid_only')


def write_ledger(data):
    LEDGER.parent.mkdir(exist_ok=True)
    temporary=LEDGER.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(LEDGER)
    doc = ROOT / 'docs/BUDGET.md'
    prefix = doc.read_text().split('\n## Phase two')[0]
    prefix = prefix.replace('The full grid has not started and requires explicit user approval.',
                            'The pilot is complete. The user subsequently approved only the redesigned phase-two study below.')
    lines = ['', '## Phase two', '',
             'The redesigned phase is authorized with a separate cap of 10 GPU-hours. '
             'The old grid is not authorized. Pending reservations charge every possible allocated GPU '
             'for the entire session timeout. Completed rows charge the larger of process lifetime and the final execution-log timestamp, multiplied by observed GPU count; '
             'quota snapshots retain the separate provisioning and billing evidence.', '',
             '| Run | Purpose | Requested GPU | Observed devices | Status | Session timeout, s | Reserved or observed device-hours |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    committed = 0
    for r in data['runs']:
        charge = r.get('actual_gpu_hours', r['reserved_gpu_hours'])
        committed += charge
        observed=', '.join(r.get('observed_gpu_names',[])) or 'Pending'
        lines.append(f"| {r['name']} | {r['purpose']} | {r['gpu']} | {observed} | {r['status']} | "
                     f"{r['timeout_s']} | {charge:.6f} |")
    lines.extend(['', f'Observed usage plus active reservations: {committed:.6f} GPU-hours. '
                  f'Unreserved phase-two allowance: {10-committed:.6f} GPU-hours.', '',
                  'All values and submission settings are recorded in `outputs/phase2_ledger.json`. '
                  'A model must complete a short calibration before its full sweep is submitted. '
                  'Across-session main-model runs remain separate statistical groups.'])
    doc.write_text(prefix + '\n'.join(lines) + '\n')


def cli(arguments, log=None):
    p = subprocess.run(['kaggle', *arguments], cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(p.stdout)
    print(p.stdout, end='')
    if p.returncode:
        raise RuntimeError('Kaggle CLI command failed; inspect its saved log')
    return p.stdout


def submit(args):
    data = ledger()
    setup_reserve=getattr(args,'setup_reserve',330)
    if setup_reserve<60 or args.timeout <= setup_reserve:
        raise ValueError('Session timeout must leave time for setup and worker finalization')
    if args.purpose == 'sweep' and args.repeats < 10:
        raise ValueError('Full sweeps require at least ten measured repeats')
    if any(r['name'] == args.name for r in data['runs']):
        raise ValueError('Run name already exists; use a distinct session ID')
    reserved = args.timeout * (2 if args.gpu == 'NvidiaTeslaT4' else 1) / 3600
    used = sum(r.get('actual_gpu_hours', r['reserved_gpu_hours']) for r in data['runs'])
    if used + reserved > 10:
        raise ValueError(f'Budget reservation rejected: {used + reserved} > 10 GPU-hours')
    models = args.models.split(',') if args.models else DEFAULT_MODELS
    if args.purpose == 'sweep':
        calibrated = set()
        for r in data['runs']:
            if r['purpose'] == 'calibration' and r['status'] == 'fetched' and r['gpu'] == args.gpu:
                calibrated.update(r.get('calibrated_models', []))
        missing = set(models) - calibrated
        if missing:
            raise ValueError('Models not yet calibrated: ' + str(sorted(missing)))
        from phase2_project import project
        projections=project()
    else:
        projections=[]
    fixture = json.loads((ROOT / 'data/phase2_conversations.json').read_text())
    spec = dict(run_id='phase2-' + args.name, gpu=args.gpu, models=models,
                purpose=args.purpose, lengths=[int(x) for x in args.lengths.split(',')],
                turns=[int(x) for x in args.turns.split(',')],
                rates_mb_s=[int(x) for x in args.rates.split(',')],
                workloads=args.workloads.split(','), repeats=args.repeats, warmups=args.warmups,
                micro_repeats=args.micro_repeats, seed=args.seed, stabilize_s=args.stabilize,
                chunk_bytes=4 * 1024 * 1024, worker_limit_s=args.timeout - setup_reserve,
                session_limit_s=args.timeout-30,setup_reserve_s=setup_reserve,
                max_allocated_gpus=2 if args.gpu == 'NvidiaTeslaT4' else 1,
                hf_secret_label=args.hf_secret_label, conversation_data=fixture,
                anomaly_profile=args.anomaly_profile,
                continue_on_model_error=args.purpose == 'calibration')
    revisions=ROOT/'configs/model_revisions.json'
    if revisions.exists():spec['model_revisions']=json.loads(revisions.read_text())
    folder = GENERATED / args.name
    folder.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'kernels/phase2/runner.py').read_text()
    marker = "CONFIG_JSON = '{}'"
    if source.count(marker) != 1:
        raise ValueError('Missing unique configuration marker')
    source = source.replace(marker, 'CONFIG_JSON = ' + repr(json.dumps(spec)))
    compile(source, str(folder / 'run.py'), 'exec')
    (folder / 'run.py').write_text(source)
    title = 'Reload Recompute P2 ' + args.name.replace('-', ' ')
    slug = title.lower().replace(' ', '-')
    reference = args.owner + '/' + slug
    metadata = dict(id=reference, title=title, code_file='run.py', language='python',
                    kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True,
                    machine_shape=args.gpu, dataset_sources=[], competition_sources=[],
                    kernel_sources=[], model_sources=[])
    baseline_metadata=RAW/'main-session-1/source/kernel-metadata.json'
    runtime=ROOT/'configs/phase2_runtime.json'
    if runtime.exists():
        image=json.loads(runtime.read_text())['docker_image']
        metadata.update(docker_image=image,docker_image_pinning_type='original')
    elif baseline_metadata.exists():
        image=json.loads(baseline_metadata.read_text()).get('docker_image')
        if image:
            metadata.update(docker_image=image,docker_image_pinning_type='original')
    (folder / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2))
    record = dict(name=args.name, purpose=args.purpose, gpu=args.gpu, reference=reference,
                  timeout_s=args.timeout, reserved_gpu_hours=reserved, status='reserved',
                  specification=spec, submitted_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    record['calibration_projections']=[r for r in projections if r['model'] in models]
    record['requested_container_image']=metadata.get('docker_image')
    data['runs'].append(record)
    write_ledger(data)  # Concrete budget and model plan exist before any GPU submission.
    cli(['quota', '--format', 'json'], RAW / args.name / 'quota-before.json')
    try:
        output = cli(['kernels', 'push', '-p', str(folder), '--accelerator', args.gpu,
                      '--timeout', str(args.timeout)], RAW / args.name / 'push.log')
        record['status'] = 'submitted'
    except Exception:
        record['status'] = 'submission_error_reservation_retained'
        write_ledger(data)
        raise
    write_ledger(data)


def fetch(args):
    data = ledger()
    run = next(r for r in data['runs'] if r['name'] == args.name)
    status = cli(['kernels', 'status', run['reference']], RAW / args.name / 'status.log')
    if not any(x in status for x in ['COMPLETE', 'ERROR', 'CANCEL']):
        print('Run still active; reservation retained.')
        return
    cli(['kernels', 'output', run['reference'], '-p', str(RAW / args.name),
         '--file-pattern', r'(^|/)phase2-output/[^/]+\.(jsonl|log|csv|txt|json)$'],
        RAW / args.name / 'fetch.log')
    quota_path=RAW/args.name/'quota-after.json'
    if quota_path.exists():
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        quota_path=RAW/args.name/f'quota-refresh-{stamp}.json'
    cli(['quota', '--format', 'json'], quota_path)
    cli(['kernels','pull',run['reference'],'-p',str(RAW/args.name/'source'),'-m'],
        RAW/args.name/'source-pull.log')
    server=json.loads((RAW/args.name/'source/kernel-metadata.json').read_text())
    run['saved_kernel_metadata']={k:server.get(k) for k in
                                  ['is_private','enable_gpu','enable_internet','kernel_type','machine_shape','docker_image']}
    if server.get('is_private') is not True:
        raise RuntimeError('Saved kernel privacy does not match the required private setting')
    result_path = RAW / args.name / 'phase2-output/results.jsonl'
    if result_path.exists():
        rows = [json.loads(line) for line in result_path.read_text().splitlines()]
        source_path=RAW/args.name/'source'/server['code_file']
        run['saved_source_sha256']=hashlib.sha256(source_path.read_bytes()).hexdigest()
        run['saved_source_matches_execution']=run['saved_source_sha256']==rows[0]['environment']['source_sha256']
        endings = [r for r in rows if r['kind'] == 'allocation_end']
        if endings:
            run['actual_gpu_hours'] = endings[-1]['conservative_gpu_hours']
            run['process_duration_s'] = endings[-1]['duration_s']
        # Include startup/conversion evidence even when the normal finalizer ran.
        logs = list((RAW / args.name).glob('*.log'))
        times = []
        for log in logs:
            try:
                events = json.loads(log.read_text())
                if isinstance(events, list):
                    times.extend(float(e['time']) for e in events if isinstance(e,dict) and 'time' in e)
            except (ValueError, TypeError):
                pass
        count = rows[0]['environment']['gpu_count']
        run['observed_gpu_names']=rows[0]['environment']['gpu_names']
        run['observed_gpu_count']=count
        if times and count:
            run['execution_log_duration_s'] = max(times)
            run['actual_gpu_hours'] = max(run.get('actual_gpu_hours',0),max(times)*count/3600)
            run['accounting_basis'] = 'max(process lifetime, final Kaggle execution-log timestamp) times observed device count'
        run['calibrated_models'] = [r['model'] for r in rows if r['kind'] == 'model_complete' and r['completed']]
        run['model_errors'] = [dict(model=r['model'], error=r['error']) for r in rows if r['kind'] == 'model_failed']
        run['complete'] = any(r['kind'] == 'run_complete' for r in rows)
        run['status'] = 'fetched'
    else:
        run['status'] = 'ended_without_results_reservation_retained'
    write_ledger(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('submit')
    p.add_argument('--name', required=True)
    p.add_argument('--owner',default=os.environ.get('KAGGLE_KERNEL_OWNER','mohiachu'))
    p.add_argument('--purpose', choices=['calibration', 'sweep', 'diagnostic'], required=True)
    p.add_argument('--gpu', default='NvidiaTeslaT4',choices=['NvidiaTeslaT4','NvidiaTeslaP100'])
    p.add_argument('--models')
    p.add_argument('--lengths', default=','.join(map(str, FULL_LENGTHS)))
    p.add_argument('--turns', default='32,256')
    p.add_argument('--rates', default='50,100,200,400,800,1600')
    p.add_argument('--workloads', default='ultrachat')
    p.add_argument('--repeats', type=int, default=10)
    p.add_argument('--warmups', type=int, default=1)
    p.add_argument('--micro-repeats', type=int, default=10)
    p.add_argument('--seed', type=int, default=7321)
    p.add_argument('--stabilize', type=int, default=10)
    p.add_argument('--timeout', type=int, required=True)
    p.add_argument('--setup-reserve',type=int,default=330,
                   help='Setup allowance, at least 60 seconds; parent also enforces the remaining session deadline')
    p.add_argument('--hf-secret-label', default='HF_TOKEN')
    p.add_argument('--anomaly-profile', action='store_true')
    p = commands.add_parser('fetch')
    p.add_argument('--name', required=True)
    args = parser.parse_args()
    lock_path = RAW / 'control/controller.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        submit(args) if args.command == 'submit' else fetch(args)
