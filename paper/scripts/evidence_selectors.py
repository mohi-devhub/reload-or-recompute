"""Document concrete release selectors without changing registered values or fits."""
import ast
import re


def describe(numbers, evidence, coverage, phase3_text):
    """Attach source fields, row predicates, operations, and rendering precision."""
    canonical = 'outputs/results.jsonl.gz'
    main = 'Qwen/Qwen2.5-1.5B'

    def set_source(key, source, selector):
        numbers[key]['source'] = source
        numbers[key]['selector'] = selector

    def raw(key, selector):
        set_source(key, canonical, selector)

    def cov_predicate(row):
        return ', '.join(f'{field}={row[field]!r}' for field in
                         ['phase', 'gpu', 'model', 'workload', 'turn_tokens'])

    cov_main = next(r for r in coverage if r['phase'] == 'phase2'
                    and r['model'] == main and r['workload'] == 'ultrachat'
                    and r['turn_tokens'] == '32')
    model_for_bracket = {'Pythia': 'EleutherAI/pythia-1.4b', 'Phi': 'microsoft/phi-2',
                         'QwenMain': main, 'QwenThree': 'Qwen/Qwen2.5-3B'}
    for key, entry in numbers.items():
        if key.startswith('Cov'):
            match = re.fullmatch(r'Cov(\d+)(Turn|Prefixes|Sessions)', key)
            row = coverage[int(match[1])]
            op = {'Turn': 'int(turn_tokens)', 'Prefixes': 'ast.literal_eval(prefixes)',
                  'Sessions': 'len(ast.literal_eval(sessions))'}[match[2]]
            set_source(key, 'outputs/consolidated_coverage.csv',
                       f'where {cov_predicate(row)}; select {op}')
        elif key.startswith('Score'):
            line, column = map(int, re.search(r'line (\d+), column (\d+)', entry['selector']).groups())
            cells = [c.strip() for c in phase3_text.splitlines()[line-1].strip('|').split('|')]
            board = cells[0].split(' ', 1)[0]
            name = {'L4': 'NVIDIA L4', 'A10': 'NVIDIA A10', 'A10G': 'NVIDIA A10G',
                    'H100': 'NVIDIA H100 80GB HBM3'}[board]
            scope = cells[1]
            predicate = f"kind='phase3_prediction_score', allocated_gpu_name={name!r}"
            if scope.startswith('session: '):
                predicate += f", run_id={scope.split(': ', 1)[1]!r}"
            elif scope != 'all':
                predicate += f", calibration_region={scope!r}"
            op = {3: 'count(correct is True) / count(correct is not null), joined as numerator / denominator',
                  4: 'count(observed_reload is null and predicted_reload is not null)',
                  5: 'count(rows)',
                  6: 'median(absolute_error_ms)'}[column]
            raw(key, f'where {predicate}; select {op}')
        elif key.startswith('KV'):
            model = entry['selector'].split('kv_bytes_per_token.', 1)[1]
            entry['selector'] = f'evidence.kv_bytes_per_token[{model!r}]'
        elif key == 'ModelCount':
            entry['selector'] = 'len(evidence.kv_bytes_per_token.keys())'
        elif entry['selector'].startswith('phase2_report_totals.'):
            entry['selector'] = 'evidence.phase2_report_totals[0].' + entry['selector'].split('.', 1)[1]
        elif re.fullmatch(r'(L4|A10G?|H100)(Correct|Resolved|Unresolved|Cells|MAE)', key):
            board, field = entry['selector'].removeprefix('gpu=').split('.', 1)
            entry['selector'] = f'where gpu={board!r}; select {field}'
        elif key.startswith(('Kaggle', 'Modal')):
            phase = 'phase2' if key.startswith('Kaggle') else 'phase3'
            field = key.removeprefix('Kaggle').removeprefix('Modal')
            operation = {'Reads': 'sum(int(positive))', 'FileSamples': 'sum(int(samples))',
                         'MinBytes': 'min(int(minimum_bytes))', 'MaxBytes': 'max(int(maximum_bytes))'}[field]
            set_source(key, 'outputs/consolidated_file_observability.csv',
                       f'where phase={phase!r}; select {operation}')
        elif 'Ratio' in key:
            board, suffix = key.split('Ratio')
            if board == 'H100': board = 'H100!'
            field = {'Yes': 'compatible_any', 'Total': 'resolved', 'Unresolved': 'unresolved'}[suffix]
            entry['selector'] = f'evidence.hypothesis_scorecards where gpu={board!r}; select {field}'
        elif key.startswith('T4Held'):
            session = re.search(r'T4Held(\d+)', key)[1]
            field = 'agreements' if key.endswith('Correct') else 'resolved_cells'
            entry['selector'] = f"evidence.heldout_session_score where run_id='phase2-main-session-{session}'; select {field}"
        elif key.startswith('Pilot'):
            if key in ['PilotPinnedLongShort', 'PilotRecomputeLongShort']:
                condition = 'cpu_pinned' if key == 'PilotPinnedLongShort' else 'recompute'
                raw(key, f"where kind='ttft', run_id='pilot-t4-v1', prefix_tokens=8192, turn_tokens=32, condition={condition!r}, valid=true; select median(wall_ms)")
            elif key == 'PilotRepeats':
                raw(key, "where kind='protocol', run_id='pilot-t4-v1'; select repeats")
            elif key == 'PilotMid':
                row = next(r for r in coverage if r['phase'] == 'pilot' and r['turn_tokens'] == '32')
                set_source(key, 'outputs/consolidated_coverage.csv',
                           f'where {cov_predicate(row)}; select ast.literal_eval(prefixes)[1]')
        elif key in ['HalfPrefix', 'HalfAdjusted']:
            field = 'predicted_prefix_bstar_mb_s' if key == 'HalfPrefix' else 'predicted_ttft_bstar_mb_s'
            raw(key, "where kind='bandwidth_crossover', run_id='phase2-qwen-half-control', model='Qwen/Qwen2.5-0.5B', workload='repeated_control', prefix_tokens=512, turn_tokens=32; select " + field)
        elif any(key == p + side for p in model_for_bracket for side in ['Low', 'High']):
            prefix = next(p for p in model_for_bracket if key.startswith(p))
            index = 0 if key.endswith('Low') else 1
            raw(key, f"where kind='bandwidth_crossover', model={model_for_bracket[prefix]!r}, workload='repeated_control', prefix_tokens=512, turn_tokens=32; select measured.brackets[0].achieved_mb_s[{index}]")
        elif 'Extrap' in key and key != 'ExtrapLength':
            board, suffix = key.split('Extrap')
            name = 'NVIDIA A10G' if board == 'A10G' else 'NVIDIA L4'
            field = {'Pred': 'predicted_ttft_ms', 'Obs': 'observed_ttft_ms', 'Error': 'absolute_error_ms'}[suffix]
            raw(key, f"where kind='phase3_prediction_score', allocated_gpu_name={name!r}, model='Qwen/Qwen2.5-3B', workload='repeated_control', prefix_tokens=32736, turn_tokens=32, condition='recompute'; select {field}")
        elif 'Spread' in key:
            board, turn_name = key.split('Spread')
            turn = 32 if turn_name == 'Short' else 256
            kind, field = ('session_spread', 'relative_range') if board == 'T4' else ('phase3_session_spread', 'range_over_median')
            gpu = {'T4': 'NvidiaTeslaT4', 'L4': 'L4', 'Ampere': 'A10'}[board]
            raw(key, f"where kind={kind!r}, gpu={gpu!r}, model={main!r}, condition='recompute', turn_tokens={turn}; select 100 * median({field}) across matched prefix lengths; Ampere rows compare A10 and A10G sessions")
        elif key in ['TorchOldError', 'TorchNewError', 'RawOldError', 'RawNewError']:
            fmt = 'torch' if key.startswith('Torch') else 'raw'
            field = 'old_signed_relative_error' if 'Old' in key else 'new_signed_relative_error'
            raw(key, f"where kind='file_rule_residual', phase='phase2', format={fmt!r}; select 100 * median(abs({field}))")
        elif key == 'H100Missing':
            raw(key, "where kind='phase3_missing_prediction_cell', gpu='H100!'; select count(rows)")
        elif key in ['AnomalyPairs', 'AnomalyReversals']:
            tail = ', prefix_minus_prefix_plus_turn_ms.ci95[0] > 0' if key == 'AnomalyReversals' else ''
            raw(key, "where kind='prefill_anomaly_pair'" + tail + '; select count(rows)')
        elif key in ['CalA10Seconds', 'CalL4Seconds']:
            board = 'a10' if key == 'CalA10Seconds' else 'l4'
            set_source(key, 'outputs/phase3_ledger.json', f"runs where name='calibration-{board}-main'; select duration_s")
        elif key in ['FullRepeats', 'CalRepeats', 'MicroRepeats', 'Warmups', 'RateLow', 'RateHigh', 'Rates', 'MainGrid'] or re.fullmatch(r'Rate\d+', key):
            field = {'FullRepeats': 'repeats', 'CalRepeats': 'calibration_repeats', 'MicroRepeats': 'calibration_micro_repeats',
                     'Warmups': 'warmups', 'RateLow': 'rates_mb_s[0]', 'RateHigh': 'rates_mb_s[-1]',
                     'Rates': 'rates_mb_s', 'MainGrid': 'main_lengths'}.get(key)
            if field is None:
                rate = int(key[4:]);field = f'rates_mb_s[{[50,100,200,400,800,1600].index(rate)}]'
            set_source(key, 'configs/phase3_plan.json', field)
        elif key == 'Bootstraps':
            raw(key, "where kind='phase3_analysis_metadata'; select bootstrap_resamples")
        elif key == 'CI':
            set_source(key, 'scripts/analyze_pilot.py',
                       'interval(): np.quantile(medians, [0.025, 0.975]); nominal coverage = 100 * (0.975 - 0.025)')
        elif key in ['SessionsT4', 'SessionsL4']:
            phase, board = ('phase2', 'T4') if key == 'SessionsT4' else ('phase3', 'L4')
            row = next(r for r in coverage if r['phase'] == phase and r['gpu'] == board and r['model'] == main and r['workload'] == 'ultrachat' and r['turn_tokens'] == '32')
            set_source(key, 'outputs/consolidated_coverage.csv', f'where {cov_predicate(row)}; select len(ast.literal_eval(sessions))')
        elif key == 'AmpereGeneration':
            raw(key, "where kind='telemetry_sample', phase='phase3', run_id in ['phase3-a10-main-1', 'phase3-a10-main-2']; select max(sample['pcie.link.gen.current'])")
        elif key == 'ShortGrid':
            set_source(key, 'configs/phase3_plan.json', 'main_lengths filtered to length <= 256')
        elif key == 'MhaGrid':
            set_source(key, 'outputs/consolidated_coverage.csv',
                       "where model in ['EleutherAI/pythia-1.4b', 'microsoft/phi-2'], turn_tokens='32'; select sorted intersection of ast.literal_eval(prefixes) across rows")
        elif key in ['Short', 'Long']:
            row = dict(cov_main, turn_tokens=str(entry['value']))
            set_source(key, 'outputs/consolidated_coverage.csv', f'where {cov_predicate(row)}; select int(turn_tokens)')
        elif key in ['Tiny', 'Small', 'Mid', 'Boundary', 'Example', 'Matched', 'LongPrefix', 'MaxMain', 'ExtrapLength']:
            row = cov_main
            if key == 'ExtrapLength':
                row = next(r for r in coverage if r['phase'] == 'phase3' and r['gpu'] == 'L4' and r['model'] == 'Qwen/Qwen2.5-3B' and r['turn_tokens'] == '32')
            index = ast.literal_eval(row['prefixes']).index(entry['value'])
            set_source(key, 'outputs/consolidated_coverage.csv', f'where {cov_predicate(row)}; select ast.literal_eval(prefixes)[{index}]')
        elif key.startswith('Cal') and key.endswith('Anchors'):
            pass  # These are already direct frozen-registration field paths.
        else:
            raise ValueError('Missing concrete selector: ' + key)

        # Rendering instructions make retained claim precision explicit. Values stay intact.
        text = entry['rendered']
        if re.fullmatch(r'[\d,]+\.\d+', text):
            rounding = f"round to {len(text.split('.')[1])} decimal places; commas are thousands separators"
        elif isinstance(entry['value'], list):
            rounding = 'no rounding; retain list order, join with comma-space, group thousands'
        elif isinstance(entry['value'], str):
            rounding = ('round median to 3 decimal places' if key.startswith('Score') and key.endswith('Col5')
                        else 'no rounding; retain integer/list/count-pair values and displayed separators')
        else:
            rounding = 'no rounding; integer, group thousands as displayed'
        entry['selector'] += '; render: ' + rounding
