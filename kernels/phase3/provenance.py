"""Scheduling adaptation with exact source hashes for protected measurement functions."""
import ast
import difflib
import hashlib

PROTECTED=['timed','flat_reload','model_run.forward','model_run.request','read_bytes','evict']

def matches_gpu(name,requested):
    allowed={'L4':{'L4'},'A10':{'A10','A10G'},'H100!':{'H100'}}
    return bool(set(name.split()) & allowed.get(requested,set()))

def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def functions(source):
    found={}
    def visit(node,path):
        for child in ast.iter_child_nodes(node):
            current=path
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                current=path+[child.name]
                found['.'.join(current)]=ast.get_source_segment(source,child)
            visit(child,current)
    visit(ast.parse(source),[])
    return {name:digest(found[name]) for name in PROTECTED}

def adapt(source):
    replacements={
        "    max_context = getattr(cfg, 'max_position_embeddings', 32768)":
        "    model_turns = SPEC.get('turns_by_model', {}).get(model_id, SPEC['turns'])\n    max_context = getattr(cfg, 'max_position_embeddings', 32768)",
        "    lengths = SPEC['lengths'].copy()":
        "    lengths = SPEC.get('lengths_by_model', {}).get(model_id, SPEC['lengths']).copy()",
        "                turns = SPEC['turns'].copy()":
        "                if SPEC['purpose'] == 'calibration':\n                    direct_micro(torch, torch_path, pageable, shapes)\n                turns = model_turns.copy()",
        "                    conditions += ['simulated_unthrottled']":
        "                    conditions += ['simulated_unthrottled']\n                    if SPEC['purpose'] == 'calibration':\n                        conditions = ['prefix_only', 'recompute', 'gpu_hit']\n                    else:\n                        conditions.remove('file_torch_staged')",
    }
    changed=source
    for old,new in replacements.items():
        assert changed.count(old)==1,old
        changed=changed.replace(old,new)
    changed=changed.replace("max(SPEC['turns'])",'max(model_turns)').replace("min(SPEC['turns'])",'min(model_turns)')
    assert functions(source)==functions(changed),'Protected measurement source changed'
    return changed

def describe(reference,historical):
    changed=adapt(reference)
    hashes=functions(reference)
    assert hashes==functions(historical),'Reference differs from executed T4 measurement functions'
    return dict(reference_source_sha256=digest(reference),historical_t4_source_sha256=digest(historical),
                adapted_source_sha256=digest(changed),protected_function_hashes=hashes,
                protected_functions_match_t4=True,
                scheduling_diff=''.join(difflib.unified_diff(reference.splitlines(True),changed.splitlines(True),
                                                           fromfile='phase2/reference.py',tofile='phase3/adapted.py')))
