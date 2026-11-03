from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'kernels/phase3'))
from provenance import adapt,functions,matches_gpu
from predict_phase3 import fit,evaluate


class FrozenReference(unittest.TestCase):
    def test_l40s_cannot_pass_as_l4(self):
        self.assertFalse(matches_gpu('NVIDIA L40S','L4'))
        self.assertTrue(matches_gpu('NVIDIA L4','L4'))

    def test_a100_cannot_pass_as_ampere_a10_tier(self):
        self.assertFalse(matches_gpu('NVIDIA A100','A10'))
        self.assertTrue(matches_gpu('NVIDIA A10G','A10'))
    def test_platform_scheduling_keeps_timed_source_identical(self):
        source=(ROOT/'kernels/phase2/runner.py').read_text()
        self.assertEqual(functions(source),functions(adapt(source)))

    def test_nested_forward_change_is_detected(self):
        source=(ROOT/'kernels/phase2/runner.py').read_text()
        changed=source.replace('selected = int(logits.argmax(dim=-1).item())','selected = 0')
        self.assertNotEqual(functions(source)['model_run.forward'],functions(changed)['model_run.forward'])


class CalibrationOnlyFit(unittest.TestCase):
    def test_exact_nonnegative_quadratic_extrapolates(self):
        xs=[64,1024,8192]
        ys=[2+.01*x+.000001*x*x for x in xs]
        model=fit(xs,ys,2)
        self.assertAlmostEqual(evaluate(model,16384),2+.01*16384+.000001*16384**2,places=7)

    def test_nonphysical_unconstrained_slope_does_not_extrapolate_negative(self):
        model=fit([1,2,3],[4,3,2],1)
        self.assertTrue(all(c>=0 for c in model['coefficients']))
        self.assertGreater(evaluate(model,100),0)


if __name__=='__main__':unittest.main()
