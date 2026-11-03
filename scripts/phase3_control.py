"""Reserve and collect bounded Modal jobs; require committed sweep predictions."""
import argparse
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'outputs/raw/phase3'
LEDGER=ROOT/'outputs/phase3_ledger.json'
OUTPUT_VOLUME='reload-recompute-phase3-results-20261103'


def load():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else dict(schema_version=3,phase='phase3',
        main_limit_usd=6,h100_limit_usd=4,infrastructure_reservation_usd=.20,runs=[])


def save(data):
    temporary=LEDGER.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2)+'\n');temporary.replace(LEDGER)
    doc=ROOT/'docs/BUDGET.md';prefix=doc.read_text().split('\n## Phase three')[0]
    lines=['','## Phase three: Modal','',
           'Main targets share a hard cap of $6. Optional H100 has a separate $4 cap and at most thirty minutes total. '
           'List-price estimates count CPU, capped RAM, GPU, initialization and teardown; credits are not deducted. '
           'A separate infrastructure reservation covers image building, temporary storage and result transfer. '
           'Tariffs are captured from [Modal pricing](https://modal.com/pricing) at submission.','',
           '| Run | GPU | Purpose | Status | Observed function wall seconds | Reserved or estimated USD |',
           '| --- | --- | --- | --- | --- | --- |']
    for r in data['runs']:
        lines.append(f"| {r['name']} | {r.get('gpu') or 'CPU'} | {r['purpose']} | {r['status']} | "
                     f"{r.get('duration_s','Pending')} | {r.get('estimated_cost_usd',r['reserved_cost_usd']):.6f} |")
    main=data['infrastructure_reservation_usd']+sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in data['runs'] if r.get('gpu')!='H100!')
    h100=sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in data['runs'] if r.get('gpu')=='H100!')
    lines.extend(['',f'Main usage plus reservations: ${main:.6f} / $6. H100: ${h100:.6f} / $4. '
                  f'Infrastructure reservation: ${data["infrastructure_reservation_usd"]:.6f}.','',
                  'Measured wall time excludes provider initialization; the estimate adds a conservative initialization/teardown allowance. '
                  'Provider billing snapshots are retained separately. No unmeasured invoice amount is claimed.'])
    doc.write_text(prefix+'\n'.join(lines)+'\n')


def price_snapshot():
    p=json.loads((ROOT/'configs/phase3_prices.json').read_text())
    now=datetime.datetime.now(datetime.timezone.utc)
    page=urlopen(p['source_url'],timeout=30).read()
    # The public tariff values are also checked against the CLI rate snapshot.
    p.update(captured_at=now.isoformat(),page_sha256=hashlib.sha256(page).hexdigest())
    (RAW/'control').mkdir(parents=True,exist_ok=True)
    (RAW/'control'/('pricing-'+now.strftime('%Y%m%dT%H%M%SZ')+'.html')).write_bytes(page)
    rates=json.loads(subprocess.check_output(['modal','billing','rates','--json'],text=True))
    (RAW/'control'/('rates-'+now.strftime('%Y%m%dT%H%M%SZ')+'.json')).write_text(json.dumps(rates,indent=2)+'\n')
    p['billing_api_hourly_rates']={k:rates[k] for k in ['gpu_hour_cost_l4','gpu_hour_cost_a10g',
        'gpu_hour_cost_h100','cpu_hour_cost','mem_gib_hour_cost']}
    for gpu,key in [('L4','gpu_hour_cost_l4'),('A10','gpu_hour_cost_a10g'),('H100!','gpu_hour_cost_h100')]:
        p['gpu_usd_per_second'][gpu]=max(p['gpu_usd_per_second'][gpu],float(rates[key])/3600)
    p['cpu_usd_per_physical_core_second']=max(p['cpu_usd_per_physical_core_second'],float(rates['cpu_hour_cost'])/3600)
    p['memory_usd_per_gib_second']=max(p['memory_usd_per_gib_second'],float(rates['mem_gib_hour_cost'])/3600)
    p['rounding_policy']='maximum of displayed per-second tariff and current billing-API hourly tariff divided by 3600'
    return p


def rate(prices,gpu):
    cpu,ram=(2,4) if gpu is None else (4,32)
    return prices['gpu_usd_per_second'].get(gpu,0)+cpu*prices['cpu_usd_per_physical_core_second']+ram*prices['memory_usd_per_gib_second']


def submit(args):
    data=load();assert not any(r['name']==args.name for r in data['runs']),'Run name already exists'
    prices=price_snapshot();gpu=None if args.prepare else args.gpu
    overhead=120
    reserved=(args.timeout+overhead)*rate(prices,gpu)
    bucket='H100!' if gpu=='H100!' else 'main'
    used=(0 if bucket=='H100!' else data['infrastructure_reservation_usd'])+sum(
        r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in data['runs']
        if (r.get('gpu')=='H100!')==(bucket=='H100!'))
    assert used+reserved<=(4 if gpu=='H100!' else 6),'Dollar reservation exceeds the authorized cap'
    if gpu=='H100!':assert args.timeout+overhead<=1800,'H100 session exceeds thirty minutes'
    spec=json.loads(Path(args.spec).read_text()) if args.spec else None
    if spec and spec['purpose']=='sweep':
        manifest=ROOT/Path(spec['prediction_manifest'])
        registered=json.loads(manifest.read_text())
        commit=spec['prediction_commit']
        subprocess.run(['git','cat-file','-e',commit+':'+str(manifest.relative_to(ROOT))],cwd=ROOT,check=True)
        frozen=subprocess.check_output(['git','show',commit+':'+str(manifest.relative_to(ROOT))],cwd=ROOT)
        assert hashlib.sha256(frozen).hexdigest()==hashlib.sha256(manifest.read_bytes()).hexdigest(),'Predictions changed after commit'
        assert registered['gpu']==gpu and registered['calibration_only'],'Wrong prediction registration'
        document=Path('docs')/('PREDICTIONS_'+gpu+'.md')
        committed_document=subprocess.check_output(['git','show',commit+':'+str(document)],cwd=ROOT)
        assert committed_document==(ROOT/document).read_bytes(),'Prediction document changed after commit'
    directory=RAW/args.name;directory.mkdir(parents=True,exist_ok=True)
    record=dict(name=args.name,gpu=gpu,purpose='prepare' if args.prepare else spec['purpose'],
                status='reserved',timeout_s=args.timeout,overhead_allowance_s=overhead,prices=prices,
                reserved_cost_usd=reserved,submitted_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                specification=spec)
    data['runs'].append(record);save(data)
    env=os.environ.copy();env.update(PHASE3_GPU=gpu or 'L4',PHASE3_TIMEOUT=str(args.timeout),
                                    PHASE3_RUN_NAME='reload-recompute-p3-'+args.name)
    command=['modal','run','-d','--write-result',str(directory/'host-result.json'),str(ROOT/'kernels/phase3/modal_app.py')]
    command+=['--prepare'] if args.prepare else ['--spec-path',str(Path(args.spec).resolve())]
    with (directory/'host.log').open('w') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record.update(status='submitted',host_pid=process.pid);save(data)
    print(json.dumps(dict(name=args.name,pid=process.pid,reserved_usd=reserved,used_plus_reserved=used+reserved)))


def collect(args):
    data=load();run=next(r for r in data['runs'] if r['name']==args.name);directory=RAW/args.name
    result=directory/'host-result.json'
    if not result.exists():
        remote='preload.json' if run['purpose']=='prepare' else run['specification']['run_id']+'/done.json'
        recovery=subprocess.run(['modal','volume','get',OUTPUT_VOLUME,remote,str(result),'--force'],cwd=ROOT,
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=45)
        (directory/'result-recovery.log').write_text(recovery.stdout)
        if recovery.returncode:
            print('No completed result yet; reservation retained');return
    outcome=json.loads(result.read_text())
    remote='preload.json' if run['purpose']=='prepare' else run['specification']['run_id']
    target=directory/'preload.json' if run['purpose']=='prepare' else directory/'output'
    subprocess.run(['modal','volume','get',OUTPUT_VOLUME,remote,str(target),'--force'],cwd=ROOT,check=True,
                   stdout=subprocess.DEVNULL)
    run.update(duration_s=outcome['duration_s'],estimated_cost_usd=(outcome['duration_s']+run['overhead_allowance_s'])*rate(run['prices'],run['gpu']),
               status='collected',outcome=outcome)
    if run['purpose']!='prepare':
        rows=[json.loads(x) for x in (target/'results.jsonl').read_text().splitlines()]
        run['complete']=any(r['kind']=='run_complete' for r in rows)
        run['model_errors']=[dict(model=r.get('model'),error=r['error']) for r in rows if r['kind']=='model_failed']
        run['environment']=next(r['environment'] for r in rows if r['kind']=='environment')
        assert run['estimated_cost_usd']<=run['reserved_cost_usd'],'Observed run exceeded its reservation'
    save(data);print(json.dumps(dict(name=args.name,status=run['status'],duration_s=run['duration_s'],estimated_cost_usd=run['estimated_cost_usd'],complete=run.get('complete'))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('submit');p.add_argument('--name',required=True);p.add_argument('--gpu',choices=['L4','A10','H100!'],default='L4')
    p.add_argument('--timeout',type=int,required=True);p.add_argument('--spec');p.add_argument('--prepare',action='store_true')
    p=commands.add_parser('collect');p.add_argument('--name',required=True)
    args=parser.parse_args();RAW.mkdir(parents=True,exist_ok=True)
    with (RAW/'control.lock').open('w') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        submit(args) if args.command=='submit' else collect(args)
