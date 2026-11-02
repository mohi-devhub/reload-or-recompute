import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'analyze_pilot.py'
spec = importlib.util.spec_from_file_location('analyze_pilot', MODULE)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AnalysisTests(unittest.TestCase):
    def test_crossing_is_bracket_not_interpolated_claim(self):
        value = analysis.crossing([512, 2048, 8192], [2, -1, -5])
        self.assertEqual(value, {'status': 'bracketed', 'intervals': [[512, 2048]]})

    def test_no_observed_crossing_does_not_create_exact_length(self):
        value = analysis.crossing([512, 2048, 8192], [-1, -2, -3])
        self.assertEqual(value['shortest_sample'], 512)
        self.assertNotIn('crossover_length', value)

    def test_bootstrap_constant_and_determinism(self):
        value = analysis.interval([7] * 12)
        self.assertEqual(value['ci95'], [7, 7])
        self.assertEqual(analysis.interval([1, 2, 4, 8]), analysis.interval([1, 2, 4, 8]))

    def test_physical_model_recovers_overhead_and_slope(self):
        value = analysis.nonnegative_fit([1e6, 2e6, 4e6], [3, 5, 9])
        self.assertAlmostEqual(value['overhead_ms'], 1)
        self.assertAlmostEqual(value['ms_per_byte'], 2e-6)
        self.assertFalse(value['constrained'])

    def test_unphysical_fit_is_flagged_and_constrained(self):
        value = analysis.nonnegative_fit([1e6, 2e6, 4e6], [4, 3, 1])
        self.assertTrue(value['constrained'])
        self.assertGreaterEqual(value['overhead_ms'], 0)
        self.assertGreaterEqual(value['ms_per_byte'], 0)


if __name__ == '__main__':
    unittest.main()
