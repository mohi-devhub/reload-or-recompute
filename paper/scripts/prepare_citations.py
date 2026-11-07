"""Build a paper-only bibliography from verified primary-source citation metadata."""
from pathlib import Path
import json

P = Path(__file__).resolve().parents[1]
catalog = json.loads((P/'sources/references_catalog.json').read_text())
bib, verified = [], []

def tex(value):
    return str(value).replace('&', r'\&')

for key, r in catalog.items():
    assert all(r.get(f) for f in ['title', 'authors', 'year', 'venue', 'source', 'source_evidence']), key
    kind = r['entry_type']
    assert kind in ['article', 'inproceedings', 'misc'], key
    authors = r.get('bibliography_authors', r['authors'])
    fields = [('author', ' and '.join(tex(a) for a in authors)),
              ('title', '{'+tex(r['title'])+'}'), ('year', r['year'])]
    if kind == 'inproceedings': fields.append(('booktitle', tex(r['venue'])))
    elif kind == 'article': fields.append(('journal', tex(r['venue'])))
    else: fields.append(('howpublished', 'arXiv:'+r['arxiv_id']))
    for name in ['volume', 'number', 'pages', 'doi']:
        if r.get(name): fields.append((name, r[name]))
    fields.append(('url', r['source']))
    bib.append('@'+kind+'{'+key+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in fields)+'\n}\n')
    verified.append(dict(key=key, **{k:r[k] for k in ['title','authors','year','venue','source','source_evidence']},
                         arxiv_id=r.get('arxiv_id'), bibliography_authors=authors,
                         scope='bibliographic metadata and qualitative context; no external performance numbers'))
(P/'references.bib').write_text('\n'.join(bib))
(P/'sources/verified_citations.json').write_text(json.dumps(verified, indent=2, ensure_ascii=False)+'\n')
lines = ['# Citation verification', '',
         'All bibliography entries are real research papers. Title, ordered authors, cited year and venue were checked against the listed arXiv or official venue pages on 2026-11-07. `sources/references_catalog.json` preserves full author lists, the selected publication version, source URLs and verification records. Direct-download hashes and web-tool metadata transcriptions are labelled separately. `sources/verified_citations.json` records the exact bibliography selection. No external performance number is adopted.', '',
         'Numeric natbib citations use `references.bib` and `plainnat`; References appears before the appendices. The former documentation-only entries are omitted in favour of research papers. Historical documentation metadata remains archived but is not cited.', '',
         '| Key | Verified title | Authors rendered in bibliography | Venue/year | Primary source |',
         '| --- | --- | --- | --- | --- |']
for r in verified:
    authors = '; '.join(r['bibliography_authors']).replace('others','et al. (full list retained in catalog)')
    lines.append('| '+r['key']+' | '+r['title']+' | '+authors+' | '+r['venue']+', '+r['year']+' | '+r['source']+' |')
lines += ['', '## Version and provenance qualifications', '',
          '- CachedAttention is the USENIX ATC 2024 paper. Its earlier arXiv v1 title is AttentionStore: Cost-effective Attention Reuse across Multi-turn Conversations in Large Language Model Serving. These are versions of the same work, not two independent systems.',
          '- Mooncake uses the FAST 2025 published title and nine-author list. The initial arXiv 2407.00079 version has a different title and author list; the entries are not blended.',
          '- CacheGen is cited at SIGCOMM 2024, as identified by the arXiv comments and the publisher record. SGLang, FlashAttention and PyTorch venue pages verify their NeurIPS editions; vLLM is verified against the SOSP program and arXiv comments. Authors are rendered as in the identified arXiv revision when a venue uses expanded or shortened names.',
          '- Pythia and GQA have verified ICML and EMNLP venue records. OPT and Qwen2.5 are cited as explicit arXiv reports; the Qwen entry is the 2024 v1 report. NumPy is cited as its verified arXiv paper, without assigning an unverified journal record.',
          '- The Llama citation is The Llama 3 Herd of Models (arXiv 2407.21783v1), a family report, not a claimed dedicated Llama-3.2 paper. The actual ungated Llama-3.2 checkpoint remains identified in the model table.',
          '- No dedicated Phi-2 research paper was verified. The official model card (https://huggingface.co/microsoft/phi-2) and Microsoft release article were inspected; no paper about another Phi version was substituted. The checkpoint identifier remains the provenance for that measured model.',
          '- Matplotlib publication fields are verified from its official paper citation (https://matplotlib.org/stable/project/citing.html). The IEEE DOI landing page was opened but robot-blocked. The official author-project citation supplies title, J. D. Hunter, 2007, Computing in Science & Engineering and DOI 10.1109/MCSE.2007.55.',
          '- LMCache, Cake and py-kvcache remain explicit arXiv-version citations. Cake combines compute and load; this study does not evaluate its overlap scheduler. py-kvcache already includes offline calibration and bandwidth frontiers.',
          '- The arXiv landing-page metadata for the file-observability reference says **Characterizing Predictability-Latency Trade-offs ...**; its experimental HTML heading says **Predictability–Throughput ...**. The bibliography keeps the verified landing-page title. This source discrepancy is unchanged.',
          '- The standalone colon separating the Qwen group label from named authors in arXiv metadata is formatting punctuation and is excluded from the author list.',
          '- For exceptionally long author lists, conventional et al. is used in the printed bibliography; all source authors remain in the catalog. Bibliographic dates, identifiers and author counts are not experimental measurements.', '']
(P/'CITATIONS.md').write_text('\n'.join(lines))
print('Generated', len(verified), 'verified research-paper references')
