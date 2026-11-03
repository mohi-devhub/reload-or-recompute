"""Presentation must preserve observed board identity and counter evidence."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from study_hardware import separate
from consolidate_study import derive


class ConsolidationTests(unittest.TestCase):
    def hardware(self):
        rows=[]
        for run,name,width in [('one','NVIDIA A10',16),('two','NVIDIA A10G',8)]:
            rows.extend([dict(phase='phase3',kind='environment',run_id=run,environment=dict(gpu_names=[name],requested_gpu='A10')),
                         dict(phase='phase3',kind='telemetry_sample',run_id=run,sample={'pcie.link.width.current':width,'pcie.link.gen.current':4})])
        return rows

    def test_ampere_scorecard_keeps_boards_separate(self):
        scores=[dict(kind='phase3_prediction_score',gpu='A10',run_id=run,correct=correct,observed_reload=correct,
            predicted_reload=True,calibration_region='anchor',absolute_error_ms=1,absolute_relative_error=.1)
            for run,correct in [('one',True),('two',False)]]
        cards=[r for r in separate(scores,self.hardware()) if r['kind']=='phase3_scorecard' and r['scope']=='all']
        self.assertEqual([(r['gpu'],r['correct_decisions'],r['resolved_decisions']) for r in cards],[('A10',1,1),('A10G',0,1)])

    def test_unexpected_link_width_cannot_enter_released_group(self):
        rows=self.hardware();rows[-1]['sample']['pcie.link.width.current']=16
        with self.assertRaisesRegex(AssertionError,'Observed link differs'):separate([],rows)

    def test_counter_interpretation_distinguishes_kaggle_and_modal(self):
        rows=[dict(phase=phase,kind='microbenchmark',condition='file_legs_raw',physical_read_bytes=count,
                   bytes=4096,prefix_tokens=16,model='fixture') for phase,count in [('phase2',4096),('phase3',0)]]
        audit={r['phase']:r for r in derive(rows)['file_observability']}
        self.assertEqual(audit['phase2']['positive'],1)
        self.assertEqual(audit['phase3']['positive'],0)
        self.assertEqual(audit['phase2']['median_physical_to_file_ratio'],1)
        self.assertEqual(audit['phase3']['median_physical_to_file_ratio'],0)


if __name__=='__main__':unittest.main()
