"""One identical queued-call retry, selected by allocation time, never performance."""
import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import phase3_control as control
NAMES=['calibration-l4-controls','calibration-l4-controls-retry']
PREFIX='reload-recompute-p3-'


def containers():return json.loads(subprocess.check_output(['modal','container','list','--json'],text=True))


def main():
    if any(c['app_name']==PREFIX+NAMES[0] for c in containers()):
        print('Original allocated; retry unnecessary');return
    folder=control.RAW/'control/specs'
    spec=json.loads((folder/(NAMES[0]+'.json')).read_text());spec['run_id']='phase3-'+NAMES[1]
    path=folder/(NAMES[1]+'.json');path.write_text(json.dumps(spec)+'\n')
    subprocess.run([sys.executable,str(ROOT/'scripts/phase3_control.py'),'submit','--name',NAMES[1],
                    '--gpu','L4','--timeout','600','--spec',str(path)],check=True)
    deadline=time.monotonic()+600;winner=None
    while time.monotonic()<deadline:
        matches=[c for c in containers() if c['app_name'] in [PREFIX+n for n in NAMES]]
        if matches:
            first=min(matches,key=lambda c:datetime.datetime.fromisoformat(c['start_time']))
            winner=first['app_name'].removeprefix(PREFIX);break
        time.sleep(5)
    loser=NAMES[1] if winner is None or winner==NAMES[0] else NAMES[0]
    apps=json.loads(subprocess.check_output(['modal','app','list','--json'],text=True))
    target=next(a for a in apps if a['description']==PREFIX+loser)
    subprocess.run(['modal','app','stop','--yes',target['app_id']],check=True)
    with (control.RAW/'control.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);data=control.load()
        for run in data['runs']:
            if run['name'] in NAMES:
                run['use_for_prediction']=run['name']!=loser
                run['allocation_selection']='first allocated container by provider start timestamp; no timing outcomes consulted'
            if run['name']==loser:run['status']='cancelled_duplicate_reservation_retained'
        control.save(data)
    print(json.dumps(dict(winner=winner,cancelled=loser,reason='allocation time, not measured performance')))


if __name__=='__main__':main()
