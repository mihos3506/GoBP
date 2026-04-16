import asyncio
import re
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

ROOT = Path('D:/GoBP')
WAVES = sorted((ROOT / 'waves').glob('*.md'))


def wave_name_from_file(name: str) -> str:
    m = re.match(r"wave_([a-zA-Z0-9]+)_brief\.md$", name)
    if m:
        return f"Wave {m.group(1).upper()}"
    if name.lower() == 'workflow.md':
        return 'Wave Workflow'
    if name.lower() == 'gobp_id_design.md':
        return 'Wave ID Design'
    return f"Wave {Path(name).stem.replace('_', ' ').title()}"


def extract_candidates(text: str):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('## TASK') or s.startswith('###'):
            out.append(s)
    seen = set(); uniq = []
    for s in out:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k); uniq.append(s)
    return uniq[:6]


def classify_type(label: str) -> str:
    l = label.lower()
    if 'flow' in l: return 'Flow'
    if 'engine' in l: return 'Engine'
    if 'entity' in l: return 'Entity'
    if 'invariant' in l: return 'Invariant'
    return 'Feature' if ('task' in l or 'feature' in l or 'migration' in l or 'viewer' in l) else 'Node'


async def run(q: str):
    idx = GraphIndex.load_from_disk(ROOT)
    return await dispatch(q, idx, ROOT)


async def main():
    s = await run("session:start actor='cursor' goal='batch materialize wave theory nodes from docs'")
    sid = s['session_id']
    created = updated = edges = 0

    for i, fp in enumerate(WAVES, 1):
        fdoc = await run(f"find:Document {fp.stem}")
        ms = fdoc.get('matches', []) if isinstance(fdoc, dict) else []
        if not ms:
            continue
        doc_id = str(ms[0].get('id',''))
        if not doc_id:
            continue

        wname = wave_name_from_file(fp.name)
        uw = await run(f"upsert:Wave dedupe_key='name' name='{wname}' description='Theory model synchronized from {fp.name}' session_id='{sid}'")
        wave_id = str(uw.get('node_id') or uw.get('existing_id') or '')
        if uw.get('ok'):
            created += 1 if uw.get('action') == 'created' else 0
            updated += 1 if uw.get('action') != 'created' else 0

        if wave_id:
            e = await run(f"edge: {wave_id} --references--> {doc_id} reason='wave references source doc'")
            if e.get('ok'): edges += 1

        text = fp.read_text(encoding='utf-8', errors='ignore')
        for raw in extract_candidates(text):
            t = re.sub(r"\*+", '', raw)
            t = re.sub(r"^#+\s*", '', t)
            t = re.sub(r"\s+", ' ', t).strip()[:96]
            if len(t) < 6:
                continue
            ntype = classify_type(t)
            name = f"{wname}: {t}"
            up = await run(
                f"upsert:{ntype} dedupe_key='name' name='{name}' spec_source='waves/{fp.name}' description='Extracted theory node from wave document' session_id='{sid}'"
            )
            if not up.get('ok'):
                continue
            nid = str(up.get('node_id') or up.get('existing_id') or '')
            created += 1 if up.get('action') == 'created' else 0
            updated += 1 if up.get('action') != 'created' else 0
            if nid:
                e = await run(f"edge: {nid} --references--> {doc_id} reason='derived from wave theory document'")
                if e.get('ok'): edges += 1

        if i % 6 == 0:
            print(f'processed_files: {i}/{len(WAVES)}')

    print('session_id:', sid)
    print('files_scanned:', len(WAVES))
    print('created_nodes:', created)
    print('updated_nodes:', updated)
    print('edges_created:', edges)


asyncio.run(main())
