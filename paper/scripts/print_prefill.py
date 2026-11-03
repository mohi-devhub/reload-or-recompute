"""Reflow the released throughput figure for legible single-column print, with no changed data or fits."""
from pathlib import Path
import subprocess,json,hashlib,tempfile,sys
P=Path(__file__).resolve().parents[1];R=P.parent
# Execute the released renderer, modifying presentation dimensions/output directory only.
source=subprocess.check_output(['git','show','v0.1.0-data:scripts/report_phase3.py'],cwd=R,text=True)
source=source.replace("fig,axes=plt.subplots(2,3,figsize=(11,7)","fig,axes=plt.subplots(3,2,figsize=(7,5.5)")
source='\n'.join(line for line in source.splitlines() if 'axes.flat[-1].text(' not in line)+'\n'
source=source.replace('fontsize=7.3)','fontsize=7,labelspacing=.05,borderpad=0,handlelength=1.8)')
source=source.replace('Frozen adjusted-rule prediction','Frozen adjusted rule').replace('Prefix-only KV bytes/token × tokens/s','Prefix-only bandwidth rule').replace('Censored median bound (up / down)','Outside tested rates')
assert 'subplots(3,2' in source
sys.path.insert(0,str(R/'scripts'))
namespace={'__file__':str(R/'scripts/report_phase3.py'),'__name__':'released_print_renderer'}
exec(compile(source,'released_print_renderer.py','exec'),namespace)
# All underlying observations are read from the data tag, not the current working tree.
import gzip
raw=subprocess.check_output(['git','show','v0.1.0-data:outputs/results.jsonl.gz'],cwd=R)
rows=[json.loads(l) for l in gzip.decompress(raw).splitlines()]
assert (R/'scripts/study_hardware.py').read_bytes()==subprocess.check_output(['git','show','v0.1.0-data:scripts/study_hardware.py'],cwd=R)
from study_hardware import separate
separated=separate([r for r in rows if r.get('phase')=='phase3' and r.get('record_origin')=='analysis'],rows)
cross=[r for r in separated if r['kind']=='phase3_bandwidth_crossover'];t4=[r for r in rows if r.get('phase')=='phase2' and r['kind']=='bandwidth_crossover']
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':8,'pdf.fonttype':42,'ps.fonttype':42})
# The renderer reads only model configs from its ROOT and writes figures/ there.
with tempfile.TemporaryDirectory() as d:
 root=Path(d);(root/'configs').mkdir();(root/'configs/phase3_t4_reference.json').write_bytes(subprocess.check_output(['git','show','v0.1.0-data:configs/phase3_t4_reference.json'],cwd=R));namespace['ROOT']=root
 namespace['figure'](cross,t4)
 for ext in ['pdf','png']:(P/'figures'/('bstar-vs-prefill.'+ext)).write_bytes((root/'figures'/('phase3_bstar_vs_prefill.'+ext)).read_bytes())
original=subprocess.check_output(['git','show','v0.1.0-data:figures/paper/bstar-vs-prefill.pdf'],cwd=R)
(P/'generated/figure_reformat.json').write_text(json.dumps(dict(reason='Original three-column plot scales its tick labels below comfortable single-column print size; reflowed to two columns. No observations, predictions, fits or brackets changed. Legend wording is shortened without changing meaning.',original_sha256=hashlib.sha256(original).hexdigest(),print_sha256=hashlib.sha256((P/'figures/bstar-vs-prefill.pdf').read_bytes()).hexdigest(),renderer_source='v0.1.0-data:scripts/report_phase3.py',changes=['subplot grid 2x3 to 3x2','canvas 11x7 to 7x5.5 inches','font defaults for actual print size','compact legend; explanatory note moved to caption','local output directory']),indent=2)+'\n')
