"""Derive bandwidth thresholds from accepted pilot timings, without GPU work."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'outputs/results.jsonl'
rows = [json.loads(line) for line in path.read_text().splitlines()]
summary = {(r['prefix_tokens'], r.get('turn_tokens'), r['condition']): r
           for r in rows if r['kind'] == 'summary'}
overhead_ms = next(r['overhead_ms'] for r in rows if r['kind'] == 'rule_calibration'
                   and r['condition'] == 'h2d_pinned')
bpt = next(r['kv_bytes_per_token_config'] for r in rows if r['kind'] == 'model_config')
derived = []
for length in [512, 2048, 8192]:
    prefill = summary[(length, None, 'prefix_only')]
    payload = length * bpt
    row = dict(schema_version=2, kind='pilot_bstar', run_id='phase2-pilot-analysis',
               model='Qwen/Qwen2.5-1.5B', gpu='Tesla T4', prefix_tokens=length,
               kv_bytes_per_token=bpt, prefill_ms=prefill['median'],
               prefix_bstar_bytes_s=payload * 1000 / prefill['median'],
               prefix_bstar_ci95_bytes_s=[payload * 1000 / prefill['ci95'][1],
                                          payload * 1000 / prefill['ci95'][0]],
               overhead_ms=overhead_ms,
               overhead_adjusted_bstar_bytes_s=payload * 1000 / (prefill['median'] - overhead_ms),
               ttft_bstar_bytes_s={str(turn): payload * 1000 / (
                   summary[(length, turn, 'recompute')]['median'] -
                   summary[(length, turn, 'gpu_hit')]['median'] - overhead_ms)
                   for turn in [32, 256]},
               source='accepted pilot summary and independent H2D calibration records')
    derived.append(row)
rows = [r for r in rows if r['kind'] != 'pilot_bstar'] + derived
path.write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in rows))
notes = ROOT / 'docs/NOTES.md'
existing = notes.read_text()
marker='\n## Phase two: pilot break-even bandwidth'
text,separator,following=existing.partition(marker)
next_heading=following.find('\n## ')
trailing=following[next_heading:] if separator and next_heading>=0 else ''
lines = ['', '## Phase two: pilot break-even bandwidth', '',
         'Phase two replaces the original full grid. The user authorizes a separate ceiling of 10 GPU-hours. '
         'Every throttled path is simulated bandwidth; it is not a measurement of a physical storage device.', '',
         '`B*_prefix(L) = L × kv_bytes_per_token / T_prefill(L) = kv_bytes_per_token × prefill_tokens_per_second(L)`. '
         'With reload fixed overhead `h`, use `B* = bytes / (T_prefill - h)` when the denominator is positive. '
         'For resumed-turn TTFT, the appropriate threshold is `bytes / (T_recompute(prefix + turn) - T_gpu_hit(turn | prefix) - h)`. '
         'The pilot anomaly and shape-dependent new-turn cost make these two thresholds differ.', '',
         '| Prefix tokens | Prefix-only B*, MB/s | Bootstrap 95% CI, MB/s | With H2D overhead, MB/s | TTFT B*, turn 32, MB/s | TTFT B*, turn 256, MB/s |',
         '| --- | --- | --- | --- | --- | --- |']
for r in derived:
    lines.append(f"| {r['prefix_tokens']} | {r['prefix_bstar_bytes_s']/1e6:.3f} | "
                 f"[{r['prefix_bstar_ci95_bytes_s'][0]/1e6:.3f}, {r['prefix_bstar_ci95_bytes_s'][1]/1e6:.3f}] | "
                 f"{r['overhead_adjusted_bstar_bytes_s']/1e6:.3f} | "
                 f"{r['ttft_bstar_bytes_s']['32']/1e6:.3f} | {r['ttft_bstar_bytes_s']['256']/1e6:.3f} |")
lines += ['', 'MB and GB are decimal throughout the bandwidth sweep. The user\'s approximate 125–180 MB/s range '
          'is supported by the prefix-only pilot medians after rounding. It is not the same as an end-to-end TTFT threshold. '
          'Source: `pilot_bstar` records in `outputs/results.jsonl`, regenerated with `python3 scripts/pilot_bstar.py`. '
          'Small KV size is a plausible contributor, not an isolated causal conclusion from one model.']
notes.write_text(text + '\n'.join(lines) + '\n' + trailing)
print('\n'.join(lines[7:]))
