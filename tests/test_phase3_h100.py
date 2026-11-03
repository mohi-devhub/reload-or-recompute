import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'kernels/phase3'))


class H100Gate(unittest.TestCase):
    def harness(self,calibration_ok=True,matching_commit=True):
        # Compile just the orchestration function; no SDK, image, or GPU creation.
        import ast
        source=(ROOT/'kernels/phase3/modal_app.py').read_text();tree=ast.parse(source)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_h100')
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name)
        planned=[dict(name='h100-test',models=['model'],lengths_by_model={'model':[256]},turns_by_model={'model':[32]},workload='ultrachat')]
        stage=dict(run_id='phase3-h100-test',models=['model'],lengths_by_model={'model':[256]},turns_by_model={'model':[32]},
                   workloads=['ultrachat'],prediction_commit=('a' if matching_commit else 'b')*40,_stage_timeout_s=100)
        manifest=json.dumps(dict(gpu='H100!',calibration_only=True))
        payload=dict(prediction_commit='a'*40,manifest_text=manifest,manifest_sha256=hashlib.sha256(manifest.encode()).hexdigest(),sweep_stages=[stage])
        calls=[]
        class Volume:
            def commit(self):pass
            def reload(self):
                (root/'outer/release.json').write_text(json.dumps(payload))
        def execute(spec,limit):
            calls.append(spec['run_id']);return dict(complete=calibration_ok or spec['run_id']=='phase3-h100-test')
        scope=dict(Path=lambda p:root if p=='/persist' else Path(p),outputs=Volume(),LIMIT=1680,GPU='H100!',
                   execute_reference=execute,json=json,os=__import__('os'))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<H100 orchestration>','exec'),scope)
        spec=dict(run_id='outer',calibration_stages=[dict(run_id='calibration')],planned_runs=planned)
        return scope['execute_h100'](spec),calls

    def test_sweep_requires_calibration_then_release(self):
        outcome,calls=self.harness()
        self.assertTrue(outcome['complete']);self.assertEqual(calls,['calibration','phase3-h100-test'])

    def test_failed_calibration_never_reaches_sweep(self):
        outcome,calls=self.harness(calibration_ok=False)
        self.assertFalse(outcome['complete']);self.assertEqual(calls,['calibration'])

    def test_release_commit_must_match_stage(self):
        outcome,calls=self.harness(matching_commit=False)
        self.assertFalse(outcome['complete']);self.assertEqual(calls,['calibration'])


class H100Admission(unittest.TestCase):
    def test_h100_cannot_start_before_required_grids_finish(self):
        import argparse
        import phase3_control as control
        prices=json.loads((ROOT/'configs/phase3_prices.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            spec=Path(folder)/'spec.json';spec.write_text(json.dumps(dict(purpose='h100_combined')))
            args=argparse.Namespace(name='h100-test',prepare=False,gpu='H100!',timeout=1680,spec=str(spec))
            data=dict(runs=[],infrastructure_reservation_usd=.2)
            with patch.object(control,'load',return_value=data),patch.object(control,'price_snapshot',return_value=prices):
                with self.assertRaisesRegex(AssertionError,'both main target grids'):control.submit(args)


if __name__=='__main__':unittest.main()
