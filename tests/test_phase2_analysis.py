import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_phase2 import crossover


class BandwidthCrossovers(unittest.TestCase):
    def test_observed_bracket_is_distinct_from_interpolation(self):
        values=[dict(target_mb_s=50,achieved_mb_s=48,delta_ms=2),
                dict(target_mb_s=100,achieved_mb_s=96,delta_ms=-2)]
        result=crossover(values)
        self.assertEqual(result['brackets'][0]['target_mb_s'],[50,100])
        self.assertAlmostEqual(result['brackets'][0]['interpolated_mb_s'],64)
        self.assertIn('not a directly sampled',result['brackets'][0]['interpretation'])

    def test_unthrottled_can_bound_the_upper_endpoint(self):
        values=[dict(target_mb_s=1600,achieved_mb_s=1500,delta_ms=3),
                dict(target_mb_s=None,achieved_mb_s=10000,delta_ms=-1)]
        result=crossover(values)
        self.assertEqual(result['brackets'][0]['target_mb_s'],[1600,None])

    def test_no_crossing_is_censored(self):
        result=crossover([dict(target_mb_s=50,achieved_mb_s=48,delta_ms=-2),
                          dict(target_mb_s=100,achieved_mb_s=97,delta_ms=-3)])
        self.assertEqual(result['upper_bound_target_mb_s'],50)
        self.assertNotIn('brackets',result)


if __name__=='__main__':
    unittest.main()
