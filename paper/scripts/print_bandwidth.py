"""Replace technical legend wording in the released GPU-bandwidth figure; data stay frozen."""
from pathlib import Path
import ast,gzip,hashlib,json,subprocess,sys,tempfile
P=Path(__file__).resolve().parents[1];R=P.parent
sys.path.insert(0,str(R/'scripts'))
source=subprocess.check_output(['git','show','v0.1.0-data:scripts/consolidate_study.py'],cwd=R,text=True)
ns={'__file__':str(R/'scripts/consolidate_study.py'),'__name__':'released_bandwidth_legend'}
exec(compile(source,'released_bandwidth_legend.py','exec'),ns)
function=next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='figures')
prefix=ast.get_source_segment(source,function).split("    cards=d['scorecards']",1)[0]
assert 'Censored bound' in prefix
prefix=prefix.replace('Censored bound','Recompute through highest rate')
exec(compile(prefix,'released_bandwidth_legend_figure.py','exec'),ns)
rows=[json.loads(line) for line in gzip.decompress(subprocess.check_output(['git','show','v0.1.0-data:outputs/results.jsonl.gz'],cwd=R)).splitlines()]
data=ns['derive'](rows)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);(root/'figures').mkdir();ns['ROOT']=root;ns['figures'](data)
 for ext in ['pdf','png']:(P/'figures'/('bstar-vs-gpu.'+ext)).write_bytes((root/'figures/paper'/('bstar-vs-gpu.'+ext)).read_bytes())
original=subprocess.check_output(['git','show','v0.1.0-data:figures/paper/bstar-vs-gpu.pdf'],cwd=R)
(P/'generated/figure_bandwidth_legend.json').write_text(json.dumps(dict(reason='Clarity revision: label unlocated crossovers as recompute through highest tested rate; no new measurements, data or fits.',original_sha256=hashlib.sha256(original).hexdigest(),print_sha256=hashlib.sha256((P/'figures/bstar-vs-gpu.pdf').read_bytes()).hexdigest(),renderer_source='v0.1.0-data:scripts/consolidate_study.py',changes=['legend text only']),indent=2)+'\n')
