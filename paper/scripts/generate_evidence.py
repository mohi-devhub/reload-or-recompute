"""Generate every empirical number and appendix table from the immutable data tag."""
from pathlib import Path
import csv,hashlib,io,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2];PAPER=ROOT/'paper';TAG='v0.1.0-data';sources={};numbers={}

def released(path):
 data=subprocess.check_output(['git','show',TAG+':'+path],cwd=ROOT);sources[path]=hashlib.sha256(data).hexdigest();return data

def j(path):return json.loads(released(path))
def rows(path):return list(csv.DictReader(io.StringIO(released(path).decode())))
def escape(s):return str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def put(key,value,source,field,claim,render=None):
 numbers[key]=dict(value=value,rendered=str(value) if render is None else render,source=source,selector=field,claim=claim)
 return r'\N{'+key+'}'

def main():
 evidence=j('outputs/claims_evidence.json');ev=evidence['evidence'];tot=ev['phase2_report_totals'][0]
 for key,value,field,claim in [('ModelCount',7,'model configurations',3),('T4Timings',tot['accepted_measurements'],'accepted_measurements',3),('T4Invalid',tot['invalid_measurements'],'invalid_measurements',3),('T4Sessions',tot['full_sessions'],'full_sessions',3),('AdjustedCorrect',tot['rule_counts']['ttft_rule_agreements'],'rule_counts.ttft_rule_agreements',5),('PrefixCorrect',tot['rule_counts']['prefix_rule_agreements'],'rule_counts.prefix_rule_agreements',5),('T4Resolved',tot['rule_counts']['resolved_comparisons'],'rule_counts.resolved_comparisons',5)]:put(key,value,'outputs/claims_evidence.json','phase2_report_totals.'+field,claim,format(value,','))
 for r in ev['scorecards']:
  gpu=r['gpu'].replace('!','')
  for suffix,field in [('Correct','correct_decisions'),('Resolved','resolved_decisions'),('Unresolved','unresolved_decisions'),('Cells','complete_cells'),('MAE','median_absolute_ttft_error_ms')]:
   value=r[field];put(gpu+suffix,value,'outputs/consolidated_scorecard.csv','gpu='+r['gpu']+'.'+field,9,f'{value:.3f}' if suffix=='MAE' else str(value))
 for phase,name,claim in [('phase2','Kaggle',16),('phase3','Modal',17)]:
  values=[r for r in ev['file_observability'] if r['phase']==phase]
  put(name+'Reads',sum(r['positive'] for r in values),'outputs/consolidated_file_observability.csv',phase+'.sum(positive)',claim,format(sum(r['positive'] for r in values),','))
  put(name+'FileSamples',sum(r['samples'] for r in values),'outputs/consolidated_file_observability.csv',phase+'.sum(samples)',claim,format(sum(r['samples'] for r in values),','))
  for suffix,field,op in [('MinBytes','minimum_bytes',min),('MaxBytes','maximum_bytes',max)]:put(name+suffix+'',op(r[field] for r in values),'outputs/consolidated_file_observability.csv',phase+'.'+field,claim,format(op(r[field] for r in values),','))
 # Exact rounded values already used by the released claim inventory.
 for key,value,claim,source,selector in [
 ('HalfPrefix',226.626,6,'docs/CLAIMS.md','claim 6 prefix-only B*'),('HalfAdjusted',2442.265,6,'docs/CLAIMS.md','claim 6 adjusted B*'),
 ('PythiaLow',798.9,7,'docs/CLAIMS.md','claim 7 Pythia achieved low'),('PythiaHigh',1597.2,7,'docs/CLAIMS.md','claim 7 Pythia achieved high'),('QwenMainLow',199.5,7,'docs/CLAIMS.md','claim 7 Qwen1.5 achieved low'),('QwenMainHigh',398.4,7,'docs/CLAIMS.md','claim 7 Qwen1.5 achieved high'),
 ('PhiLow',799.2,7,'docs/CLAIMS.md','claim 7 Phi achieved low'),('PhiHigh',1598.4,7,'docs/CLAIMS.md','claim 7 Phi achieved high'),('QwenThreeLow',99.9,7,'docs/CLAIMS.md','claim 7 Qwen3 achieved low'),('QwenThreeHigh',199.7,7,'docs/CLAIMS.md','claim 7 Qwen3 achieved high'),
 ('A10GExtrapPred',8041.096,10,'docs/CLAIMS.md','claim 10 A10G recompute predicted'),('A10GExtrapObs',13914.555,10,'docs/CLAIMS.md','claim 10 A10G recompute observed'),('A10GExtrapError',5873.459,10,'docs/CLAIMS.md','claim 10 A10G recompute absolute error'),('L4ExtrapPred',13088.360,10,'docs/CLAIMS.md','claim 10 L4 recompute predicted'),('L4ExtrapObs',18022.902,10,'docs/CLAIMS.md','claim 10 L4 recompute observed'),('L4ExtrapError',4934.542,10,'docs/CLAIMS.md','claim 10 L4 recompute absolute error'),
 ('T4SpreadShort',12.341,14,'docs/CLAIMS.md','claim 14 T4 N32 median spread'),('T4SpreadLong',14.847,14,'docs/CLAIMS.md','claim 14 T4 N256 median spread'),('L4SpreadShort',4.956,14,'docs/CLAIMS.md','claim 14 L4 N32 median spread'),('L4SpreadLong',4.417,14,'docs/CLAIMS.md','claim 14 L4 N256 median spread'),('AmpereSpreadShort',23.611,15,'docs/CLAIMS.md','claim 15 N32 matched relative range'),('AmpereSpreadLong',22.664,15,'docs/CLAIMS.md','claim 15 N256 matched relative range'),
 ('TorchOldError',11.780,19,'docs/CLAIMS.md','claim 19 torch old APE'),('TorchNewError',3.097,19,'docs/CLAIMS.md','claim 19 torch corrected APE'),('RawOldError',3.107,19,'docs/CLAIMS.md','claim 19 raw old APE'),('RawNewError',3.086,19,'docs/CLAIMS.md','claim 19 raw corrected APE'),
 ('H100Missing',52,20,'docs/CLAIMS.md','claim 20 unfinished cells'),('AnomalyReversals',0,21,'docs/CLAIMS.md','claim 21 positive lower endpoints'),('AnomalyPairs',4,21,'docs/CLAIMS.md','claim 21 comparisons'),('CalA10Seconds',42.5,9,'docs/PHASE3_REPORT.md','calibration-a10-main wall seconds'),('CalL4Seconds',63.4,9,'docs/PHASE3_REPORT.md','calibration-l4-main wall seconds')]:
  put(key,value,source,selector,claim,format(value,',.3f') if key in ['HalfPrefix','HalfAdjusted','A10GExtrapPred','A10GExtrapObs','A10GExtrapError','L4ExtrapPred','L4ExtrapObs','L4ExtrapError'] else str(value))
 # A direct membership check prevents hand-entered claim values drifting from the release.
 claims_text=released('docs/CLAIMS.md').decode();phase3_text=released('docs/PHASE3_REPORT.md').decode()
 for key,r in numbers.items():
  if r['source']=='docs/CLAIMS.md':assert str(r['value']) in claims_text or f"{r['value']:.3f}" in claims_text,key
  if key.startswith('Cal'):assert str(r['value']) in phase3_text,key
 for gpu,yes,total,unresolved in [(r['gpu'].replace('!',''),r['compatible_any'],r['resolved'],r['unresolved']) for r in ev['hypothesis_scorecards']]:
  for suffix,v in [('RatioYes',yes),('RatioTotal',total),('RatioUnresolved',unresolved)]:put(gpu+suffix,v,'outputs/claims_evidence.json','hypothesis_scorecards.gpu='+gpu+'.'+suffix,11)
 for i,r in enumerate(ev['heldout_session_score'],2):
  for suffix,field in [('Correct','agreements'),('Resolved','resolved_cells')]:put('T4Held'+str(i)+suffix,r[field],'outputs/claims_evidence.json',r['run_id']+'.'+field,8)
 for key,value in [('Short',32),('Long',256),('Tiny',16),('Small',64),('Mid',128),('Boundary',256),('Example',512),('Matched',1024),('LongPrefix',8192),('MaxMain',16384),('ExtrapLength',32736)]:put(key,value,'outputs/consolidated_coverage.csv','prefix or new-turn length present in coverage',3,format(value,','))
 for key,value in [('FullRepeats',10),('CalRepeats',3),('MicroRepeats',5),('Warmups',1),('Bootstraps',10000),('CI',95),('SessionsT4',3),('SessionsL4',2),('RateLow',50),('RateHigh',1600)]:
  source='docs/PHASE3_PROTOCOL.md' if key not in ['Bootstraps','CI','SessionsT4'] else 'docs/PHASE3_REPORT.md'
  if key=='Bootstraps':source='outputs/results.jsonl.gz'
  put(key,value,source,'released measurement protocol / referenced canonical analysis metadata',3,format(value,','))
 put('Rates','50, 100, 200, 400, 800, 1600','docs/PHASE2_PROTOCOL.md','Rate-limited copies are simulated bandwidth',3,'50, 100, 200, 400, 800, 1,600')
 for value in [100,200,400,800,1600]:put('Rate'+str(value),value,'docs/PHASE2_PROTOCOL.md','simulated-bandwidth target grid',12,format(value,','))
 put('PilotMid',2048,'outputs/consolidated_coverage.csv','pilot prefixes',1,'2,048')
 put('PilotRepeats',12,'docs/CLAIMS.md','claim 1 measured repeats',1)
 put('AmpereGeneration',4,'docs/PHASE3_REPORT.md','active PCIe generation for A10 and A10G',15)
 put('MainGrid','16,64,128,256,512,1024,2048,4096,8192,16384','outputs/consolidated_coverage.csv','phase3 main-model prefixes',3,'16, 64, 128, 256, 512, 1,024, 2,048, 4,096, 8,192, 16,384')
 put('ShortGrid','16,64,128,256','docs/CLAIMS.md','claim 13 common short prefixes',13,'16, 64, 128, 256')
 put('MhaGrid','64,256,512,1024','docs/CLAIMS.md','claim 18 matched prefixes',18,'64, 256, 512, 1,024')
 modeltext=[r'\begin{tabular}{llr}',r'\toprule Checkpoint & Layout & KV bytes/token \\ \midrule']
 for idx,(model,b) in enumerate(ev['kv_bytes_per_token'].items()):
  k='KV'+str(idx);put(k,b,'outputs/claims_evidence.json','kv_bytes_per_token.'+model,4,format(b,','));layout='MHA' if any(x in model for x in ['pythia','phi-2','opt-']) else 'GQA'
  modeltext.append(r'\path{'+model+'} & '+layout+' & '+r'\N{'+k+r'} \\')
 modeltext.extend([r'\bottomrule',r'\end{tabular}']);(PAPER/'generated/models.tex').write_text('\n'.join(modeltext)+'\n')
 coverage=rows('outputs/consolidated_coverage.csv');cov=[r'\begin{longtable}{p{.78in}p{1.43in}crp{2.55in}r}',r'\caption{Complete measured coverage. U is UltraChat; R is repeated text. Sessions counts separate allocations, not repeat rounds. Calibration and incomplete H100 cells are excluded.}\label{tab:coverage}\\',r'\toprule Phase/board & Model & Text & Turn & Prefix tokens & Sessions\\\midrule\endfirsthead',r'\toprule Phase/board & Model & Text & Turn & Prefix tokens & Sessions\\\midrule\endhead']
 for i,r in enumerate(coverage):
  model=r['model'].split('/')[-1].replace('Qwen2.5-','Qwen ').replace('Llama-3.2-3B-Instruct','Llama 3.2-3B');phase={'pilot':'Pilot','phase2':'T4','phase3':r['gpu'].replace('!','')}[r['phase']];prefix=__import__('ast').literal_eval(r['prefixes']);sessions=__import__('ast').literal_eval(r['sessions'])
  vals=[put('Cov'+str(i)+'Turn',int(r['turn_tokens']),'outputs/consolidated_coverage.csv','row '+str(i)+'.turn_tokens',3),put('Cov'+str(i)+'Prefixes',prefix,'outputs/consolidated_coverage.csv','row '+str(i)+'.prefixes',3,', '.join(format(v,',') for v in prefix)),put('Cov'+str(i)+'Sessions',len(sessions),'outputs/consolidated_coverage.csv','row '+str(i)+'.sessions',3)]
  cov.append(phase+' & '+model+' & '+('U' if r['workload']=='ultrachat' else 'R')+' & '+vals[0]+' & '+vals[1]+' & '+vals[2]+r' \\')
 cov.extend([r'\bottomrule\end{longtable}']);(PAPER/'generated/coverage.tex').write_text('\n'.join(cov)+'\n')
 board=['\\begin{longtable}{p{1.1in}p{1.8in}rrrr}',r'\caption{Frozen scores by observed board and calibration region or session. Error is median absolute TTFT error in milliseconds, over all complete predicted conditions. Decisions exclude unresolved paired intervals.}\label{tab:scores}\\',r'\toprule Board/link & Scope & Correct/resolved & Unresolved & Cells & Error\\\midrule\endfirsthead',r'\toprule Board/link & Scope & Correct/resolved & Unresolved & Cells & Error\\\midrule\endhead']
 score_section=phase3_text.split('## Frozen prediction scorecard',1)[1].split('\nThe calibrated rule',1)[0]
 score_offset=phase3_text[:phase3_text.index(score_section)].count('\n')
 for i,line in enumerate(score_section.splitlines(),score_offset):
  if not line.startswith('| ') or not any(line.startswith('| '+g) for g in ['L4 (','A10 (','A10G (','H100 (']):continue
  cells=[s.strip() for s in line.strip('|').split('|')]
  if len(cells)!=7 or not re.fullmatch(r'\d+ / \d+',cells[2]):continue
  label=cells[0].split(' / ')[0].replace('(PCIe 3 x16)','x16').replace('(PCIe 4 x16)','x16').replace('(PCIe 4 x8)','x8').replace('(PCIe 5 x16)','x16')
  scope=cells[1].replace('session: phase3-','').replace('interpolation','interpolate').replace('extrapolation','extrapolate');mac=[]
  for c in [2,3,4,5]:mac.append(put('Score'+str(i)+'Col'+str(c),cells[c],'docs/PHASE3_REPORT.md','scorecard table line '+str(i+1)+', column '+str(c+1),9,cells[c]))
  board.append(label+' & '+scope+' & '+' & '.join(mac)+r' \\')
 board.append(r'\bottomrule\end{longtable}');(PAPER/'generated/scorecards.tex').write_text('\n'.join(board)+'\n')
 for key,r in numbers.items():released(r['source'])
 text=['% Generated only from v0.1.0-data. Do not edit empirical values by hand.',r'\newcommand{\N}[1]{\csname nr@#1\endcsname}']
 for k,r in numbers.items():text.append(r'\expandafter\def\csname nr@'+k+r'\endcsname{'+escape(r['rendered'])+'}')
 (PAPER/'generated/numbers.tex').write_text('\n'.join(text)+'\n');(PAPER/'generated/number_registry.json').write_text(json.dumps(numbers,indent=2)+'\n')
 manifest=json.loads((PAPER/'DATA_SOURCES.json').read_text());manifest['files'].update(sources);(PAPER/'DATA_SOURCES.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('Generated',len(numbers),'source-mapped values and appendix tables from',TAG)

if __name__=='__main__':main()
