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


def extract_candidates(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('## TASK'):
            out.append((s, 'task_heading'))
        elif s.startswith('###'):
            out.append((s, 'section_heading'))
        elif s.startswith('**Goal:**'):
            out.append((s.replace('**Goal:**', '').strip(), 'goal'))
    seen = set()
    uniq: list[tuple[str, str]] = []
    for t, k in out:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append((t, k))
    return uniq[:16]


def classify_type(label: str) -> str:
    l = label.lower()
    if 'flow' in l:
        return 'Flow'
    if 'engine' in l:
        return 'Engine'
    if 'entity' in l:
        return 'Entity'
    if 'invariant' in l:
        return 'Invariant'
    if 'feature' in l or 'viewer' in l or 'layout' in l or 'migration' in l or 'task' in l:
        return 'Feature'
    return 'Node'


async def safe_dispatch(q: str, retries: int = 5):
    for i in range(retries):
        try:
            idx = GraphIndex.load_from_disk(ROOT)
            return await dispatch(q, idx, ROOT)
        except PermissionError:
            await asyncio.sleep(0.2 * (i + 1))
    return {'ok': False, 'error': 'PermissionError after retries'}


async def main() -> None:
    sess = await safe_dispatch("session:start actor='cursor' goal='materialize wave docs into typed theory nodes with traceability edges retry-safe'")
    sid = sess['session_id']

    created = 0
    updated = 0
    edge_ok = 0
    skipped_docs = 0

    for i, fp in enumerate(WAVES, 1):
        find_doc = await safe_dispatch(f"find:Document {fp.stem}")
        matches = find_doc.get('matches', []) if isinstance(find_doc, dict) else []
        if not matches:
            skipped_docs += 1
            continue
        doc_id = str(matches[0].get('id', ''))
        if not doc_id:
            skipped_docs += 1
            continue

        wave_name = wave_name_from_file(fp.name)
        up_wave = await safe_dispatch(
            f"upsert:Wave dedupe_key='name' name='{wave_name}' description='Wave model synchronized from {fp.name}' session_id='{sid}'"
        )
        wave_id = str(up_wave.get('node_id') or up_wave.get('existing_id') or '')
        if up_wave.get('ok'):
            if up_wave.get('action') == 'created':
                created += 1
            else:
                updated += 1

        if wave_id:
            e = await safe_dispatch(
                f"edge: {wave_id} --references--> {doc_id} reason='wave node references source document'"
            )
            if e.get('ok'):
                edge_ok += 1

        text = fp.read_text(encoding='utf-8', errors='ignore')
        for raw, source_kind in extract_candidates(text):
            title = re.sub(r"\*+", '', raw)
            title = re.sub(r"^#+\s*", '', title)
            title = re.sub(r"\s+", ' ', title).strip()
            if len(title) < 6:
                continue
            title = title[:100]

            node_type = classify_type(title)
            node_name = f"{wave_name}: {title}"
            desc = f"Extracted from {fp.name} ({source_kind})"

            q = (
                f"upsert:{node_type} dedupe_key='name' "
                f"name='{node_name}' description='{desc}' "
                f"spec_source='waves/{fp.name}' session_id='{sid}'"
            )
            up = await safe_dispatch(q)
            if not up.get('ok'):
                continue

            nid = str(up.get('node_id') or up.get('existing_id') or '')
            if up.get('action') == 'created':
                created += 1
            else:
                updated += 1

            if nid:
                e1 = await safe_dispatch(
                    f"edge: {nid} --references--> {doc_id} reason='derived from wave document content'"
                )
                if e1.get('ok'):
                    edge_ok += 1
                if wave_id:
                    e2 = await safe_dispatch(
                        f"edge: {wave_id} --relates_to--> {nid} reason='wave includes this theory node'"
                    )
                    if e2.get('ok'):
                        edge_ok += 1

        if i % 8 == 0:
            print(f'processed_files: {i}/{len(WAVES)}')

    print('session_id:', sid)
    print('files_scanned:', len(WAVES))
    print('created_nodes:', created)
    print('updated_nodes:', updated)
    print('edges_created:', edge_ok)
    print('docs_without_match:', skipped_docs)


asyncio.run(main())
