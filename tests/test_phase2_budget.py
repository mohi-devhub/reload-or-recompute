import argparse
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase2_control


class BudgetGate(unittest.TestCase):
    def args(self,**overrides):
        values=dict(name='never_submit',timeout=900,purpose='sweep',repeats=10,
                    gpu='NvidiaTeslaT4',models='Qwen/Qwen2.5-1.5B')
        values.update(overrides)
        return argparse.Namespace(**values)

    @patch.object(phase2_control,'cli')
    @patch.object(phase2_control,'ledger')
    def test_budget_rejection_happens_before_any_kaggle_call(self,ledger,cli):
        ledger.return_value={'runs':[dict(name='old',reserved_gpu_hours=9.9)]}
        with self.assertRaisesRegex(ValueError,'Budget reservation rejected'):
            phase2_control.submit(self.args())
        cli.assert_not_called()

    @patch.object(phase2_control,'cli')
    @patch.object(phase2_control,'ledger')
    def test_other_gpu_calibration_does_not_authorize_sweep(self,ledger,cli):
        ledger.return_value={'runs':[dict(name='calibration',purpose='calibration',status='fetched',
                                         gpu='NvidiaTeslaP100',calibrated_models=['Qwen/Qwen2.5-1.5B'],
                                         reserved_gpu_hours=.1,actual_gpu_hours=.01)]}
        with self.assertRaisesRegex(ValueError,'not yet calibrated'):
            phase2_control.submit(self.args())
        cli.assert_not_called()


if __name__=='__main__':
    unittest.main()
