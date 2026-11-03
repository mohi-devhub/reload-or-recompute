"""Losslessly materialize or package the canonical JSONL archive."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',action='store_true');p.add_argument('--force',action='store_true');args=p.parse_args()
    plain=ROOT/'outputs/results.jsonl';archive=plain.with_suffix('.jsonl.gz');manifest=ROOT/'outputs/results_archive.json'
    if args.pack:
        with plain.open('rb') as source,archive.open('wb') as destination:
            with gzip.GzipFile(filename='',mode='wb',fileobj=destination,mtime=0) as stream:shutil.copyfileobj(source,stream)
        info=dict(kind='results_archive',format='gzip',canonical_path='outputs/results.jsonl',archive_path='outputs/results.jsonl.gz',
                  uncompressed_bytes=plain.stat().st_size,uncompressed_sha256=digest(plain),compressed_sha256=digest(archive))
        manifest.write_text(json.dumps(info,indent=2)+'\n')
    else:
        info=json.loads(manifest.read_text());assert digest(archive)==info['compressed_sha256'],'Compressed archive checksum mismatch'
        if plain.exists() and not args.force:
            assert digest(plain)==info['uncompressed_sha256'],'Existing results differ; use --force to restore the archived canonical records'
            print('Canonical results already match the archive');return
        temporary=plain.with_suffix('.unpack.tmp')
        with gzip.open(archive,'rb') as source,temporary.open('wb') as destination:shutil.copyfileobj(source,destination)
        assert digest(temporary)==info['uncompressed_sha256'],'Uncompressed archive checksum mismatch'
        temporary.replace(plain)
    print(json.dumps(info))


if __name__=='__main__':main()
