"""One bounded sandbox allocation probe; this produces no benchmark timings."""
import asyncio
import datetime
import fcntl
import json
from pathlib import Path
import sys
import time
import modal

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import phase3_control as control


def update(fields):
    with (control.RAW/'control.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);data=control.load()
        next(r for r in data['runs'] if r['name']=='l4-sandbox-probe').update(fields);control.save(data)


async def main():
    with (control.RAW/'control.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);data=control.load()
        assert not any(r['name']=='l4-sandbox-probe' for r in data['runs'])
        prices=control.price_snapshot();resources=dict(cpu_physical=1,memory_gib=1)
        # GPU Sandbox rates are standard; capped CPU and RAM use non-preemptible tariffs.
        prices['cpu_usd_per_physical_core_second']=max(.00003942,3*prices['cpu_usd_per_physical_core_second'])
        prices['memory_usd_per_gib_second']=max(.00000667,3*prices['memory_usd_per_gib_second'])
        prices['sandbox_cpu_memory_multiplier']=3
        reserve=180*control.rate(prices,'L4',resources)
        used=data['infrastructure_reservation_usd']+sum(r.get('estimated_cost_usd',r['reserved_cost_usd']) for r in data['runs'] if r.get('gpu')!='H100!')
        assert used+reserve<=6
        data['runs'].append(dict(name='l4-sandbox-probe',gpu='L4',purpose='allocation_probe',status='reserved',
             timeout_s=60,overhead_allowance_s=120,prices=prices,resources=resources,reserved_cost_usd=reserve,
             submitted_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             specification=dict(run_id='phase3-l4-sandbox-probe',purpose='allocation_probe',gpu='L4')))
        control.save(data)
    start=time.monotonic();sandbox=None
    try:
        app=await modal.App.lookup.aio('reload-recompute-p3-l4-sandbox-probe',create_if_missing=True)
        sandbox=await modal.Sandbox.create.aio(app=app,name='l4-availability',gpu='L4',cpu=(1,1),memory=(1024,1024),
                       image=modal.Image.debian_slim(python_version='3.13'),timeout=60)
        update(dict(sandbox_id=sandbox.object_id,status='probe_submitted'))
        await sandbox.wait_until_ready.aio(timeout=90)
        process=await sandbox.exec.aio('nvidia-smi',timeout=10)
        output=await process.stdout.read.aio();error=await process.stderr.read.aio()
        update(dict(status='probe_completed_reservation_retained',nvidia_smi=output,stderr=error))
        print(output)
    except Exception as error:
        update(dict(status='probe_failed_reservation_retained',error_type=type(error).__name__,error=str(error)))
        print(type(error).__name__,str(error))
    finally:
        if sandbox:
            try:await asyncio.wait_for(sandbox.terminate.aio(),timeout=30)
            except Exception as error:update(dict(termination_error_type=type(error).__name__))
        update(dict(probe_host_wall_s=time.monotonic()-start))


if __name__=='__main__':asyncio.run(main())
