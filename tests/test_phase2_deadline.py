import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

RUNNER=Path(__file__).resolve().parents[1]/'kernels/phase2/runner.py'


class ParentDeadline(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        previous=Path.cwd()
        try:
            os.chdir(self.directory.name)
            spec=importlib.util.spec_from_file_location('reference_deadline_test',RUNNER)
            self.runner=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.runner)
        finally:
            os.chdir(previous)
        self.runner.SPEC=dict(run_id='deadline-test',worker_limit_s=900,session_limit_s=970)
        self.runner.START=100
        self.runner.ENV=dict(gpu_count=2)

    def tearDown(self):
        self.directory.cleanup()

    def invoke(self,now):
        r=self.runner
        self.child=Mock()
        self.child.wait.return_value=0
        with patch.object(r,'environment'),patch.object(r,'telemetry',return_value=(None,None)), \
             patch.object(r,'emit') as emit,patch.object(r.time,'time',return_value=now), \
             patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
             patch.object(r.subprocess,'Popen',return_value=self.child) as launch:
            self.launch=launch
            self.emit=emit
            r.main()

    def test_slow_setup_reduces_actual_child_timeout(self):
        self.invoke(now=900)
        args=self.launch.call_args.args[0]
        self.assertEqual(args[-2:],['--worker-limit-s','170'])
        self.child.wait.assert_called_once_with(timeout=170)

    def test_exhausted_setup_starts_no_worker(self):
        with self.assertRaisesRegex(RuntimeError,'Setup exhausted'):
            self.invoke(now=1050)
        self.launch.assert_not_called()


if __name__=='__main__':unittest.main()
