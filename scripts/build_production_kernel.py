"""Build the production-only submission from the reviewed pilot implementation."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / 'kernels/pilot/pilot.py').read_text()
replacements = {
    "RUN_ID = os.environ.get('ROR_RUN_ID', 'pilot-t4-v1')":
        "RUN_ID = os.environ.get('ROR_RUN_ID', 'pilot-t4-production-v1')",
    'PRODUCTION_ONLY = False': 'PRODUCTION_ONLY = True',
}
for before, after in replacements.items():
    if source.count(before) != 1:
        raise ValueError(f'Expected one source marker: {before}')
    source = source.replace(before, after)
destination = root / 'kernels/production/production.py'
destination.write_text(source)
print(destination)
