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


async def run(q: str):
    idx = GraphIndex.load_from_disk(ROOT)
    return await dispatch(q, idx, ROOT)


async def main():
    sess = await run("session:start actor='cursor' goal='link wave docs to theory/product nodes with edges'")
    sid = sess['session_id']
    ok_docs = 0
    ok_nodes = 0
    ok_edges = 0

    for fp in WAVES:
        fd = await run(f"find:Document {fp.stem}")
        matches = fd.get('matches', []) if isinstance(fd, dict) else []
        if not matches:
            continue
        doc_id = str(matches[0].get('id',''))
        if not doc_id:
            continue
        ok_docs += 1

        wave_name = wave_name_from_file(fp.name)
        uw = await run(f"upsert:Wave dedupe_key='name' name='{wave_name}' description='Wave container for theory-to-product traceability' session_id='{sid}'")
        wave_id = str(uw.get('node_id') or uw.get('existing_id') or '')

        theory_name = f"{wave_name}: theory to product mapping"
        un = await run(
            f"upsert:Feature dedupe_key='name' name='{theory_name}' description='Represents functional/entity/feature intent extracted from {fp.name}' spec_source='waves/{fp.name}' session_id='{sid}'"
        )
        node_id = str(un.get('node_id') or un.get('existing_id') or '')
        if un.get('ok'):
            ok_nodes += 1

        for q in [
            (f"edge: {node_id} --references--> {doc_id} reason='theory node is grounded in wave document'") if node_id else '',
            (f"edge: {wave_id} --references--> {doc_id} reason='wave node references source document'") if wave_id else '',
            (f"edge: {wave_id} --relates_to--> {node_id} reason='wave contains this theory product mapping node'") if wave_id and node_id else '',
        ]:
            if not q:
                continue
            er = await run(q)
            if er.get('ok'):
                ok_edges += 1
            await asyncio.sleep(0.05)

    print('session_id:', sid)
    print('docs_linked:', ok_docs)
    print('theory_nodes_upserted:', ok_nodes)
    print('edges_created:', ok_edges)


asyncio.run(main())
