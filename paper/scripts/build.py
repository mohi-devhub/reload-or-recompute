"""Compile locally with pdflatex/bibtex; never invokes experiments or remote services."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
P=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--tex-bin');p.add_argument('--texmf-home');a=p.parse_args()
env=os.environ.copy()
if a.tex_bin:env['PATH']=str(Path(a.tex_bin).expanduser().resolve())+os.pathsep+env.get('PATH','')
if a.texmf_home:env['TEXMFHOME']=str(Path(a.texmf_home).expanduser().resolve())
state=P/'build/tex-state';state.mkdir(parents=True,exist_ok=True);env['TEXMFVAR']=str(state.resolve())
for exe in ['pdflatex','bibtex']:assert shutil.which(exe,path=env['PATH']),exe+' is required; supply --tex-bin if it is not on PATH'
commands=[['pdflatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','main.tex'],['bibtex','main']]+[['pdflatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','main.tex']]*2
bibtex_warnings=[]
for i,cmd in enumerate(commands):
 r=subprocess.run(cmd,cwd=P,env=env,capture_output=True,text=True);(P/'build'/f'pass-{i}-{cmd[0]}.txt').write_text(r.stdout+r.stderr)
 if cmd[0]=='bibtex':bibtex_warnings.extend(line for line in (r.stdout+r.stderr).splitlines() if re.search(r'Warning--|Warning:',line))
 if r.returncode:print((r.stdout+r.stderr)[-4500:]);raise SystemExit(r.returncode)
log=(P/'main.log').read_text();assert not re.search(r'undefined references|Citation .* undefined|Reference .* undefined',log),'Unresolved reference/citation'
info=subprocess.check_output(['pdfinfo',str(P/'main.pdf')],text=True);pages=int(re.search(r'Pages:\s+(\d+)',info)[1]);aux=(P/'main.aux').read_text();body=int(re.search(r'\\newlabel\{references:start\}\{\{[^}]*\}\{(\d+)\}',aux)[1])-1;appendix=int(re.search(r'\\newlabel\{app:coverage\}\{\{[^}]*\}\{(\d+)\}',aux)[1]);latex_warnings=[s for s in log.splitlines() if 'Overfull' in s or 'Warning:' in s];warnings=list(dict.fromkeys(latex_warnings+bibtex_warnings))
reference_count=len(re.findall(r'\\bibcite\{',aux));assert reference_count>0,'No bibliography entries in compiled manuscript'
result=dict(pdf='paper/main.pdf',pages=pages,body_pages=body,references_and_appendix_pages=pages-body,reference_pages=appendix-body-1,appendix_pages=pages-appendix+1,reference_count=reference_count,pdf_sha256=hashlib.sha256((P/'main.pdf').read_bytes()).hexdigest(),commands=commands,engine=subprocess.check_output(['pdflatex','--version'],env=env,text=True).splitlines()[0],warnings=warnings,warning_sources=dict(latex=latex_warnings,bibtex=bibtex_warnings))
(P/'BUILD.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
