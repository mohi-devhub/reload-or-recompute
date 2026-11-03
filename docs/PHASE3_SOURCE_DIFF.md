# Phase-three source provenance

Protected timing and request functions are byte-identical to the executed T4 source. Platform environment, telemetry, persistence, and calibration scheduling live outside them.

Reference source SHA256: `73dd9a4fdd9d43191673ecf07cfb763b3600f8fa8144a0b82951b565b7b68793`

Adapted scheduling SHA256: `b40c09f50bb30f2252bd4f6d15e6e04cc3551b0343d0a960049507f1cd08a85e`

```diff
--- phase2/reference.py
+++ phase3/adapted.py
@@ -220,16 +220,17 @@
         return cache.to_legacy_cache() if hasattr(cache, 'to_legacy_cache') else cache
 
     backend = [SDPBackend.EFFICIENT_ATTENTION, SDPBackend.MATH]
+    model_turns = SPEC.get('turns_by_model', {}).get(model_id, SPEC['turns'])
     max_context = getattr(cfg, 'max_position_embeddings', 32768)
-    lengths = SPEC['lengths'].copy()
-    boundary = max_context - max(SPEC['turns'])
+    lengths = SPEC.get('lengths_by_model', {}).get(model_id, SPEC['lengths']).copy()
+    boundary = max_context - max(model_turns)
     if boundary < max(lengths) and boundary > min(lengths):
         lengths.append(boundary)
     lengths = sorted(set(lengths))
     rng = random.Random(SPEC['seed'])
     rng.shuffle(lengths)
     worksets = SPEC.get('workloads', ['repeated_control'])
-    token_sets = {w: source_tokens(tokenizer, w, max(SPEC['lengths']) + max(SPEC['turns']))
+    token_sets = {w: source_tokens(tokenizer, w, max(SPEC['lengths']) + max(model_turns))
                   for w in worksets}
     done = set()
     for line in (OUT / 'results.jsonl').read_text().splitlines():
@@ -251,7 +252,7 @@
             ids, provenance = token_sets[workload]
             emit('workload', **provenance)
             for length in lengths:
-                if length + min(SPEC['turns']) > max_context:
+                if length + min(model_turns) > max_context:
                     emit('shape_skipped', workload=workload, prefix_tokens=length,
                          reason='prefix plus new turn exceeds native model context', max_context=max_context)
                     continue
@@ -307,7 +308,9 @@
                         emit('microbenchmark', condition='h2d_' + tier, repeat=repeat, valid=True,
                              bytes=payload_bytes, **transfer)
                         del copied
-                turns = SPEC['turns'].copy()
+                if SPEC['purpose'] == 'calibration':
+                    direct_micro(torch, torch_path, pageable, shapes)
+                turns = model_turns.copy()
                 rng.shuffle(turns)
                 for turn_length in turns:
                     if length + turn_length > max_context:
@@ -341,6 +344,10 @@
                                   'file_torch_direct', 'file_torch_staged', 'file_raw_staged']
                     conditions += ['simulated_' + str(rate) + '_MBps' for rate in rates]
                     conditions += ['simulated_unthrottled']
+                    if SPEC['purpose'] == 'calibration':
+                        conditions = ['prefix_only', 'recompute', 'gpu_hit']
+                    else:
+                        conditions.remove('file_torch_staged')
 
                     def request(condition):
                         details = {}
```
