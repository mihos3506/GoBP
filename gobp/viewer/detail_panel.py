"""HTML fragments for viewer detail panel (v2).

Used by tests and as the canonical layout reference; browser ``index.html`` mirrors this.
"""

from __future__ import annotations

import html
import json
from typing import Any


def _esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def _desc_info_code(node: dict[str, Any]) -> tuple[str, str]:
    """Prose vs code: v3 uses top-level ``code``; v2 object uses description.info/code."""
    raw = node.get("description")
    top_code = str(node.get("code", "") or "").strip()
    if isinstance(raw, dict):
        info = str(raw.get("info", "") or "")
        code = str(raw.get("code", "") or "").strip()
        if not code and top_code:
            code = top_code
        return info, code
    info = str(raw or "")
    return info, top_code


def render_standard_panel(node: dict[str, Any]) -> str:
    """Standard v2 panel: breadcrumb, lifecycle/read_order, description info+code, relationships."""
    group = str(node.get("group", "") or "").strip()
    parts = [p.strip() for p in group.split(">")] if group else []
    crumbs = " > ".join(parts) if parts else ""
    crumb_html = ""
    if crumbs:
        crumb_html = f'<div class="v2-breadcrumb">◈ {_esc(crumbs)}</div>'

    ntype = str(node.get("type", ""))
    title = str(node.get("name", ""))
    life = str(node.get("lifecycle", "") or "")
    ro = str(node.get("read_order", "") or "")
    meta_line = []
    if life:
        meta_line.append(f"lifecycle: {_esc(life)}")
    if ro:
        meta_line.append(f"read_order: {_esc(ro)}")
    meta_html = (
        f'<div class="v2-meta">{" &nbsp;|&nbsp; ".join(meta_line)}</div>' if meta_line else ""
    )

    info, code = _desc_info_code(node)
    desc_html = ""
    if info or code:
        desc_html = '<div class="v2-section"><div class="v2-h">DESCRIPTION</div>'
        if info:
            desc_html += f'<div class="v2-desc-info">{_esc(info)}</div>'
        if code:
            desc_html += f'<div class="v2-h">CODE</div><pre class="v2-code">{_esc(code)}</pre>'
        desc_html += "</div>"

    return (
        f'{crumb_html}<div class="v2-type">{_esc(ntype)}</div>'
        f'<div class="v2-title">{_esc(title)}</div>{meta_html}{desc_html}'
    )


def render_errorcase_panel(node: dict[str, Any]) -> str:
    """ErrorCase layout: code, severity, trigger, handling, user_message, dev_note, context, fix_history."""
    code = str(node.get("code", "") or "")
    sev = str(node.get("severity", "") or "")
    trig = str(node.get("trigger", "") or "")
    handling = str(node.get("handling", "") or "")
    fix = str(node.get("fix", "") or "")
    user_msg = str(node.get("user_message", "") or "")
    dev_note = str(node.get("dev_note", "") or "")
    ctx = node.get("context")
    if ctx is None:
        ctx_obj: dict[str, Any] = {}
    elif isinstance(ctx, dict):
        ctx_obj = ctx
    else:
        ctx_obj = {"value": ctx}
    fix_hist = node.get("fix_history") or []

    parts: list[str] = [
        '<div class="v2-breadcrumb">◈ Error &gt; ErrorCase</div>',
        '<div class="v2-type">ERROR CASE</div>',
        f'<div class="v2-title">{_esc(node.get("name", ""))}</div>',
    ]
    if code or sev:
        parts.append('<div class="v2-section">')
        if code:
            parts.append(f'<div><span class="v2-k">code</span> {_esc(code)}</div>')
        if sev:
            parts.append(f'<div><span class="v2-k">severity</span> {_esc(sev)}</div>')
        parts.append("</div>")

    def _sec(title: str, body: str) -> str:
        if not body.strip():
            return ""
        return (
            f'<div class="v2-section"><div class="v2-h">{_esc(title)}</div>'
            f'<div class="v2-desc-info">{_esc(body)}</div></div>'
        )

    parts.append(_sec("TRIGGER", trig))
    parts.append(_sec("SYSTEM RESPONSE", handling))
    parts.append(_sec("FIX", fix))
    parts.append(_sec("USER MESSAGE", user_msg))
    parts.append(_sec("DEV NOTE", dev_note))

    if ctx_obj:
        parts.append(
            '<div class="v2-section"><div class="v2-h">CONTEXT</div>'
            f'<pre class="v2-raw">{_esc(json.dumps(ctx_obj, ensure_ascii=False, indent=2))}</pre></div>'
        )

    if fix_hist:
        parts.append('<div class="v2-section"><div class="v2-h">FIX HISTORY</div><ul class="v2-fixhist">')
        for item in fix_hist:
            if isinstance(item, dict):
                line = json.dumps(item, ensure_ascii=False)
            else:
                line = str(item)
            parts.append(f"<li>{_esc(line)}</li>")
        parts.append("</ul></div>")

    return "".join(parts)


def render_invariant_panel(node: dict[str, Any]) -> str:
    """Invariant: rule, scope, enforcement."""
    rule = str(node.get("rule", "") or "")
    scope = str(node.get("scope", "") or "")
    enf = str(node.get("enforcement", "") or node.get("enforced_by", "") or "")
    parts = [
        '<div class="v2-breadcrumb">◈ Constraint &gt; Invariant</div>',
        '<div class="v2-type">INVARIANT</div>',
        f'<div class="v2-title">{_esc(node.get("name", ""))}</div>',
    ]
    if rule:
        parts.append(
            f'<div class="v2-section"><div class="v2-h">RULE</div>'
            f'<div class="v2-desc-info">{_esc(rule)}</div></div>'
        )
    if scope:
        parts.append(
            f'<div class="v2-section"><div class="v2-h">SCOPE</div>'
            f'<div class="v2-desc-info">{_esc(scope)}</div></div>'
        )
    if enf:
        parts.append(
            f'<div class="v2-section"><div class="v2-h">ENFORCEMENT</div>'
            f'<div class="v2-desc-info">{_esc(enf)}</div></div>'
        )
    return "".join(parts)


def render_knowledge_panel(node: dict[str, Any]) -> str:
    """Decision / Lesson* — reuse standard with type emphasis."""
    base = render_standard_panel(node)
    return f'<div class="v2-knowledge">{base}</div>'


def render_panel(node: dict[str, Any]) -> str:
    """Dispatch by node type (viewer v2)."""
    ntype = str(node.get("type", ""))
    if ntype == "ErrorCase":
        return render_errorcase_panel(node)
    if ntype == "Invariant":
        return render_invariant_panel(node)
    if ntype in (
        "Decision",
        "LessonRule",
        "LessonSkill",
        "LessonDev",
        "LessonCTO",
        "LessonQA",
    ):
        return render_knowledge_panel(node)
    return render_standard_panel(node)
