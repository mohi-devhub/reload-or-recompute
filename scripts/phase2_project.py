"""Create explicit planning estimates from short calibrations and pilot length scaling."""
import json
from pathlib import Path
import statistics

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def project():
    ledger = json.loads((ROOT / 'outputs/phase2_ledger.json').read_text())
    pilot = [json.loads(x) for x in (ROOT / 'outputs/results.jsonl').read_text().splitlines()]
    pilot_summary = {(r['measurement_kind'], r['prefix_tokens'], r.get('turn_tokens'), r['condition']): r['median']
                     for r in pilot if r['kind'] == 'summary'}
    full_path=ROOT/'outputs/phase2_results.jsonl'
    phase2_summaries=[]
    if full_path.exists():
        phase2_summaries=[r for r in map(json.loads,full_path.read_text().splitlines())
                          if r['kind']=='phase2_summary' and r['run_id']=='phase2-main-session-1']
    full_times={(r['prefix_tokens'],r['turn_tokens'],r['condition']):r['median'] for r in phase2_summaries}
    timebase='first complete phase-two main-model session' if full_times else 'pilot'

    def pilot_time(kind, length, turn, condition):
        if full_times:
            key_condition='prefix_only' if kind=='prefill' else condition
            key_turn=32 if turn is None else turn
            xs=np.array(sorted(k[0] for k in full_times if k[1:]==(key_turn,key_condition)),dtype=float)
            ys=np.array([full_times[(int(x),key_turn,key_condition)] for x in xs])
            return float(np.interp(length,xs,ys))
        xs = np.array([512, 2048, 8192], dtype=float)
        ys = np.array([pilot_summary[(kind, int(x), turn, condition)] for x in xs])
        if length < xs[0]:
            return float(ys[0])
        if length > xs[-1]:
            return float(ys[-1] * length / xs[-1])
        return float(np.interp(length, xs, ys))

    result = []
    for run in ledger['runs']:
        if run['purpose'] != 'calibration' or run['status'] != 'fetched':
            continue
        rows = [json.loads(x) for x in (ROOT / 'outputs/raw/phase2' / run['name'] /
                                       'phase2-output/results.jsonl').read_text().splitlines()]
        for model in run.get('calibrated_models', []):
            config = next(r for r in rows if r['kind'] == 'model_config' and r['model'] == model)
            measurements = [r for r in rows if r['kind'] == 'measurement' and r['model'] == model
                            and r['prefix_tokens'] == 512 and r['valid']]
            rec = statistics.median(r['wall_ms'] for r in measurements if r['condition'] == 'recompute')
            hit = statistics.median(r['wall_ms'] for r in measurements if r['condition'] == 'gpu_hit')
            scale = rec / pilot_time('ttft',512,32,'recompute')
            tail_scale = hit / pilot_time('ttft',512,32,'gpu_hit')
            bpt = config['kv_bytes_per_token']
            limit = config['config'].get('max_position_embeddings', 32768)
            lengths = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
            if limit - 256 < max(lengths):
                lengths.append(limit - 256)
            lengths = sorted(set(x for x in lengths if x + 32 <= limit))
            micros = [r for r in rows if r['kind'] == 'microbenchmark' and r['model'] == model
                      and r['prefix_tokens'] == 512]
            copy_per_byte = statistics.median(r['transfer_ms'] / r['bytes'] for r in micros
                                              if r['condition'] == 'h2d_pinned')
            file_per_byte = statistics.median((r['raw_read_ms'] + r['deserialize_ms'] + r['transfer_ms']) /
                                              r['bytes'] for r in micros if r['condition'].startswith('file_legs_'))
            seconds = 0
            for length in lengths:
                payload = bpt * length
                for turn in [32, 256]:
                    if length + turn > limit:
                        continue
                    prefill = pilot_time('prefill', length, None, 'prefix_only') * scale
                    recompute = pilot_time('ttft', length, turn, 'recompute') * scale
                    tail = pilot_time('ttft', length, turn, 'gpu_hit') * tail_scale
                    throttle = sum(payload / (rate * 1e6) for rate in [50, 100, 200, 400, 800, 1600])
                    per_round_ms = prefill + recompute + 12 * tail + 8 * payload * copy_per_byte + 3 * payload * file_per_byte
                    seconds += 11 * (per_round_ms / 1000 + throttle)
                seconds += 10 * (2 * payload * file_per_byte + 2 * payload * copy_per_byte) / 1000
            result.append(dict(model=model, calibration_run=run['name'], kv_bytes_per_token=bpt,
                               attention_family=config['attention_family'], native_context=limit,
                               planned_lengths=lengths, repeats=10, warmups=1, turns=[32, 256],
                               projected_worker_s=seconds,
                               projected_two_device_hours=seconds * 2 / 3600,
                               suggested_timeout_s=max(900, int(seconds * 1.25 + 390)),
                               timing_base=timebase,
                               assumptions='pilot interpolation and proportional endpoint extrapolation; '
                               'calibration model/pilot recompute and tail ratios; exact requested pacing time; '
                               'linear byte-cost extrapolation for file/copy legs; no memory-fit guarantee; '
                               '25 percent worker margin plus setup reservation'))
    output = ROOT / 'outputs/phase2_projection.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    for r in result:
        print({k:v for k,v in r.items() if k not in ['assumptions', 'planned_lengths']})
    return result


if __name__ == '__main__':
    project()
