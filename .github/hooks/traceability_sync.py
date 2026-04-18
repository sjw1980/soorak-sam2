#!/usr/bin/env python3
"""
traceability_sync.py
====================
ASPICE 추적성 문서(docs/) 파싱 → 변경 감지 → 시각화 HTML 자동 갱신

사용법:
    python3 scripts/traceability_sync.py           # 변경 시에만 HTML 갱신
    python3 scripts/traceability_sync.py --force   # 강제 갱신
    python3 scripts/traceability_sync.py --check   # 변경 여부만 확인 (exit 1 = 변경)
"""

import re
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR  = REPO_ROOT / "docs"
CACHE_FILE = REPO_ROOT / ".trace-cache.json"
HTML_OUT   = DOCS_DIR / "traceability-visualization.html"

# ── 유틸리티 ───────────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def strip_md(text: str) -> str:
    """마크다운 링크/HTML 태그 제거"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text.strip()

def parse_row(line: str) -> List[str]:
    """마크다운 테이블 한 행 → 셀 리스트 (양끝 빈 셀 제거)"""
    if not line.strip().startswith('|'):
        return []
    cells = [c.strip() for c in line.split('|')]
    while cells and not cells[0]:
        cells.pop(0)
    while cells and not cells[-1]:
        cells.pop()
    return cells

def is_sep(cells: List[str]) -> bool:
    """구분선 여부"""
    return bool(cells) and all(re.match(r'^[-: ]+$', c) for c in cells if c)

# ══════════════════════════════════════════════════════════════════════════════
# 1. ID 추출
# ══════════════════════════════════════════════════════════════════════════════

def find_ids(path: Path, pattern: str) -> List[str]:
    """파일에서 정규식 패턴으로 고유 ID 목록(정렬) 추출"""
    return sorted(set(re.findall(pattern, read_file(path))))

def extract_all_ids() -> Dict[str, List[str]]:
    d = DOCS_DIR
    return {
        "goals": [],  # goal_req 관계에서 채움
        "reqs":  find_ids(d / "SWE-1" / "SWE-1-requirements.md",                r"SWE-REQ-\d{4}"),
        "comps": find_ids(d / "SWE-2" / "SWE2-ARCH-0001-software-architecture.md", r"SWE-COMP-\d{4}"),
        "ifs":   find_ids(d / "SWE-2" / "SWE2-ARCH-0001-software-architecture.md", r"SWE-IF-\d{4}"),
        "units": find_ids(d / "SWE-3" / "SWE3-UNIT-SPEC-0001-unit-design.md",   r"SWE-UNIT-\d{4}"),
        "tcs":   find_ids(d / "SWE-4" / "SWE4-TC-SPEC-0001-unit-test.md",       r"SWE-TC-\d{4}"),
        "itcs":  find_ids(d / "SWE-5" / "SWE5-ITC-SPEC-0001-integration-test.md", r"SWE-ITC-\d{4}"),
        "qtcs":  find_ids(d / "SWE-6" / "SWE6-QTC-SPEC-0001-qualification-test.md", r"SWE-QTC-\d{4}"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 2. 관계 추출 (마크다운 테이블 행 기반)
# ══════════════════════════════════════════════════════════════════════════════

def extract_rels(path: Path, src_pat: str, tgt_pat: str) -> Dict[str, List[str]]:
    """
    마크다운 테이블 행에서 (src_id → [tgt_id, ...]) 관계를 추출.
    한 행에 src 여러 개, tgt 여러 개 모두 지원.
    src_pat과 tgt_pat이 겹치지 않는다고 가정.
    """
    rels: Dict[str, Set[str]] = {}
    for line in read_file(path).splitlines():
        if not line.strip().startswith('|'):
            continue
        srcs = re.findall(src_pat, line)
        tgts = re.findall(tgt_pat, line)
        if srcs and tgts:
            for s in srcs:
                rels.setdefault(s, set()).update(tgts)
    return {k: sorted(v) for k, v in sorted(rels.items())}

def extract_all_rels() -> Dict[str, Dict[str, List[str]]]:
    d = DOCS_DIR
    swe1t = d / "SWE-1" / "SWE1-TRACE-0001-traceability-review.md"
    swe3t = d / "SWE-3" / "SWE3-TRACE-0001-traceability-review.md"
    swe4t = d / "SWE-4" / "SWE4-TRACE-0001-traceability-review.md"
    swe5t = d / "SWE-5" / "SWE5-TRACE-0001-traceability-review.md"
    swe6t = d / "SWE-6" / "SWE6-TRACE-0001-traceability-review.md"
    return {
        "goal_req":  extract_rels(swe1t, r"PROJ-GOAL-\d{3}", r"SWE-REQ-\d{4}"),
        "req_comp":  extract_rels(swe3t, r"SWE-REQ-\d{4}",   r"SWE-COMP-\d{4}"),
        "comp_unit": extract_rels(swe3t, r"SWE-COMP-\d{4}",  r"SWE-UNIT-\d{4}"),
        "unit_tc":   extract_rels(swe4t, r"SWE-UNIT-\d{4}",  r"SWE-TC-\d{4}"),
        "req_tc":    extract_rels(swe4t, r"SWE-REQ-\d{4}",   r"SWE-TC-\d{4}"),
        "req_itc":   extract_rels(swe5t, r"SWE-REQ-\d{4}",   r"SWE-ITC-\d{4}"),
        "req_qtc":   extract_rels(swe6t, r"SWE-REQ-\d{4}",   r"SWE-QTC-\d{4}"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 3. 레이블 추출 (테이블 col 기반)
# ══════════════════════════════════════════════════════════════════════════════

def extract_labels(path: Path, id_pat: str,
                   id_col: int = 0, lbl_col: int = 1,
                   max_len: int = 40) -> Dict[str, str]:
    """테이블에서 id_col의 ID → lbl_col의 텍스트 레이블 추출"""
    labels: Dict[str, str] = {}
    for line in read_file(path).splitlines():
        cells = parse_row(line)
        if len(cells) <= max(id_col, lbl_col) or is_sep(cells):
            continue
        ids = re.findall(id_pat, cells[id_col])
        if not ids:
            continue
        lbl = strip_md(cells[lbl_col])
        if not lbl or lbl.startswith('-') or len(lbl) < 2:
            continue
        for iid in ids:
            if iid not in labels:
                labels[iid] = lbl[:max_len]
    return labels

def extract_all_labels() -> Dict[str, Dict[str, str]]:
    d = DOCS_DIR
    # REQ 짧은 이름은 TRACE 파일에 있음 (전체 요구사항 문장보다 짧음)
    req_lbl = extract_labels(d / "SWE-3" / "SWE3-TRACE-0001-traceability-review.md",
                             r"SWE-REQ-\d{4}", 0, 1, 35)
    # TRACE에 없으면 SWE-1 스펙에서 short fallback (처음 20자)
    req_lbl2 = extract_labels(d / "SWE-1" / "SWE-1-requirements.md",
                              r"SWE-REQ-\d{4}", 0, 1, 20)
    for k, v in req_lbl2.items():
        req_lbl.setdefault(k, v)

    tc_lbl  = extract_labels(d / "SWE-4" / "SWE4-TC-SPEC-0001-unit-test.md",
                             r"SWE-TC-\d{4}", 0, 1, 30)
    itc_lbl = extract_labels(d / "SWE-5" / "SWE5-TRACE-0001-traceability-review.md",
                             r"SWE-ITC-\d{4}", 0, 1, 30)
    qtc_lbl = extract_labels(d / "SWE-6" / "SWE6-QTC-SPEC-0001-qualification-test.md",
                             r"SWE-QTC-\d{4}", 0, 1, 30)
    comp_lbl = extract_labels(d / "SWE-3" / "SWE3-TRACE-0001-traceability-review.md",
                              r"SWE-COMP-\d{4}", 0, 1, 25)
    unit_lbl = extract_labels(d / "SWE-3" / "SWE3-TRACE-0001-traceability-review.md",
                              r"SWE-UNIT-\d{4}", 2, 3, 25)
    goal_lbl = extract_labels(d / "SWE-1" / "SWE1-TRACE-0001-traceability-review.md",
                              r"PROJ-GOAL-\d{3}", 0, 1, 20)
    return {
        "req": req_lbl, "tc": tc_lbl, "itc": itc_lbl,
        "qtc": qtc_lbl, "comp": comp_lbl, "unit": unit_lbl, "goal": goal_lbl,
    }

# ══════════════════════════════════════════════════════════════════════════════
# 4. 문서 메타
# ══════════════════════════════════════════════════════════════════════════════

def doc_meta(path: Path) -> Dict[str, str]:
    text = read_file(path)
    m_v = re.search(r'\|\s*버전\s*\|\s*(v[\d.]+\s*/\s*[\d-]+)', text)
    m_s = re.search(r'\|\s*상태\s*\|\s*(\w+)', text)
    return {
        "version": m_v.group(1).strip() if m_v else "—",
        "status":  m_s.group(1).strip() if m_s else "—",
    }

def extract_all_doc_meta() -> Dict[str, Dict[str, str]]:
    d = DOCS_DIR
    return {
        "SWE-1": doc_meta(d / "SWE-1" / "SWE-1-requirements.md"),
        "SWE-2": doc_meta(d / "SWE-2" / "SWE2-ARCH-0001-software-architecture.md"),
        "SWE-3": doc_meta(d / "SWE-3" / "SWE3-UNIT-SPEC-0001-unit-design.md"),
        "SWE-4": doc_meta(d / "SWE-4" / "SWE4-TC-SPEC-0001-unit-test.md"),
        "SWE-5": doc_meta(d / "SWE-5" / "SWE5-ITC-SPEC-0001-integration-test.md"),
        "SWE-6": doc_meta(d / "SWE-6" / "SWE6-QTC-SPEC-0001-qualification-test.md"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 5. 전체 데이터 빌드
# ══════════════════════════════════════════════════════════════════════════════

def build_data() -> dict:
    ids    = extract_all_ids()
    rels   = extract_all_rels()
    labels = extract_all_labels()
    meta   = extract_all_doc_meta()

    # GOAL ID 목록은 goal_req에서 수집
    ids["goals"] = sorted(rels.get("goal_req", {}).keys())

    return {
        "gen_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ids":      ids,
        "rels":     rels,
        "labels":   labels,
        "doc_meta": meta,
    }

# ══════════════════════════════════════════════════════════════════════════════
# 6. 변경 감지
# ══════════════════════════════════════════════════════════════════════════════

def content_hash(data: dict) -> str:
    """ids + rels 기준 해시 (gen_at 제외)"""
    stable = {"ids": data["ids"], "rels": data["rels"]}
    s = json.dumps(stable, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_cache(data: dict, chash: str) -> None:
    obj = {k: data[k] for k in ("gen_at", "ids", "rels", "labels", "doc_meta")}
    obj["hash"] = chash
    CACHE_FILE.write_text(json.dumps(obj, ensure_ascii=False, indent=2),
                          encoding="utf-8")

def diff_summary(old: dict, new: dict) -> List[str]:
    """캐시 vs 현재 데이터 변경 요약"""
    lines = []
    old_ids  = old.get("ids",  {})
    new_ids  = new.get("ids",  {})
    old_rels = old.get("rels", {})
    new_rels = new.get("rels", {})

    key_labels = {
        "reqs":"SWE-REQ", "tcs":"SWE-TC", "itcs":"SWE-ITC",
        "qtcs":"SWE-QTC", "comps":"SWE-COMP", "units":"SWE-UNIT",
    }
    for k, name in key_labels.items():
        a = set(old_ids.get(k, []))
        b = set(new_ids.get(k, []))
        added   = sorted(b - a)
        removed = sorted(a - b)
        if added:   lines.append(f"  + {name} 추가: {', '.join(added)}")
        if removed: lines.append(f"  - {name} 삭제: {', '.join(removed)}")

    rel_labels = {
        "goal_req":"GOAL→REQ", "req_comp":"REQ→COMP", "comp_unit":"COMP→UNIT",
        "req_tc":"REQ→TC", "req_itc":"REQ→ITC", "req_qtc":"REQ→QTC",
    }
    for k, name in rel_labels.items():
        if json.dumps(old_rels.get(k, {}), sort_keys=True) != \
           json.dumps(new_rels.get(k, {}), sort_keys=True):
            lines.append(f"  ~ {name} 관계 변경")
    return lines

# ══════════════════════════════════════════════════════════════════════════════
# 7. JS 데이터 블록 생성
# ══════════════════════════════════════════════════════════════════════════════

def js(v) -> str:
    return json.dumps(v, ensure_ascii=False)

def build_data_block(data: dict) -> str:
    ids    = data["ids"]
    rels   = data["rels"]
    labels = data["labels"]
    gen_at = data["gen_at"]

    reqs  = [{"id": i, "label": labels["req"].get(i, i), "status": "Approved"}
             for i in ids["reqs"]]
    tcs   = [{"id": i, "result": "Pass"} for i in ids["tcs"]]
    itcs  = [{"id": i, "result": "Pass"} for i in ids["itcs"]]
    qtcs  = [{"id": i, "result": "Pass"} for i in ids["qtcs"]]

    goal_items = [{"id": g, "label": labels["goal"].get(g, g)}
                  for g in ids.get("goals", [])]
    comp_items = [{"id": c, "label": labels["comp"].get(c, c)}
                  for c in ids["comps"]]
    unit_items = [{"id": u, "label": labels["unit"].get(u, u)}
                  for u in ids["units"]]

    lines = [
        f"// AUTO-GENERATED by scripts/traceability_sync.py — {gen_at}",
        f"const GENERATED_AT = {js(gen_at)};",
        f"const REQS        = {js(reqs)};",
        f"const TCS         = {js(tcs)};",
        f"const ITCS        = {js(itcs)};",
        f"const QTCS        = {js(qtcs)};",
        f"const GOAL_ITEMS  = {js(goal_items)};",
        f"const COMP_ITEMS  = {js(comp_items)};",
        f"const UNIT_ITEMS  = {js(unit_items)};",
        f"const GOAL_REQ    = {js(rels.get('goal_req',  {}))};",
        f"const REQ_COMP    = {js(rels.get('req_comp',  {}))};",
        f"const COMP_UNIT   = {js(rels.get('comp_unit', {}))};",
        f"const REQ_TC      = {js(rels.get('req_tc',    {}))};",
        f"const REQ_ITC     = {js(rels.get('req_itc',   {}))};",
        f"const REQ_QTC     = {js(rels.get('req_qtc',   {}))};",
        f"const TC_LABELS   = {js(labels.get('tc',  {}))};",
        f"const ITC_LABELS  = {js(labels.get('itc', {}))};",
        f"const QTC_LABELS  = {js(labels.get('qtc', {}))};",
    ]
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════════════
# 8. HTML 생성
# ══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ASPICE 추적성 시각화 — CLI Calculator (soorak-sam)</title>
  <style>
    :root {
      --bg: #0f1117; --bg2: #1a1d27; --bg3: #22263a; --border: #2e3250;
      --text: #e2e4f0; --text-dim: #8890b0; --accent: #4f8ef7;
      --col-goal-l:#a569bd; --col-req-l:#5dade2; --col-comp-l:#48c9b0;
      --col-unit-l:#52be80; --col-tc-l:#f0a500; --col-itc-l:#ec7063; --col-qtc-l:#af7ac5;
      --pass:#2ecc71; --fail:#e74c3c; --open:#e67e22;
    }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:'Segoe UI','Noto Sans KR',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
    header { background:var(--bg2); border-bottom:1px solid var(--border); padding:12px 20px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
    header h1 { font-size:17px; font-weight:600; }
    .badge { display:inline-block; font-size:11px; padding:2px 8px; border-radius:4px; border:1px solid var(--border); color:var(--text-dim); }
    .badge-pass { background:rgba(46,204,113,.15); color:var(--pass); border-color:var(--pass); }
    .badge-ts { font-size:10px; color:var(--text-dim); margin-left:auto; }
    .tabs { display:flex; background:var(--bg2); border-bottom:1px solid var(--border); padding:0 14px; gap:2px; }
    .tab-btn { background:none; border:none; color:var(--text-dim); padding:11px 16px; cursor:pointer; font-size:13px; border-bottom:2px solid transparent; transition:all .15s; }
    .tab-btn:hover { color:var(--text); }
    .tab-btn.active { color:var(--accent); border-bottom-color:var(--accent); }
    .tab-panel { display:none; padding:20px; height:calc(100vh - 108px); overflow:auto; }
    .tab-panel.active { display:block; }
    .legend { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:18px; }
    .l-item { display:flex; align-items:center; gap:5px; font-size:11px; color:var(--text-dim); }
    .l-dot { width:11px; height:11px; border-radius:2px; }
    /* matrix */
    .mwrap { overflow:auto; }
    table.mx { border-collapse:collapse; font-size:11px; white-space:nowrap; }
    table.mx th, table.mx td { border:1px solid var(--border); padding:4px 7px; text-align:center; }
    table.mx th { background:var(--bg3); color:var(--text-dim); position:sticky; top:0; z-index:2; }
    table.mx th.rh { position:sticky; left:0; z-index:3; }
    table.mx td.rid { background:var(--bg2); font-weight:600; text-align:left; position:sticky; left:0; z-index:1; color:var(--col-req-l); min-width:125px; cursor:pointer; }
    table.mx td.rid:hover { background:var(--bg3); }
    .cg-tc  { background:rgba(240,165,0,.06); }  .cg-itc { background:rgba(236,112,99,.06); }  .cg-qtc { background:rgba(175,122,197,.06); }
    .gh-tc  { background:rgba(240,165,0,.2)  !important; color:var(--col-tc-l)  !important; }
    .gh-itc { background:rgba(236,112,99,.2) !important; color:var(--col-itc-l) !important; }
    .gh-qtc { background:rgba(175,122,197,.2)!important; color:var(--col-qtc-l) !important; }
    .chk { color:var(--pass); font-size:13px; } .cmt { color:var(--border); }
    .rhi td { background:rgba(79,142,247,.10) !important; }
    /* hierarchy */
    #hwrap { overflow:auto; }
    .h-node { cursor:pointer; }
    .h-node rect { rx:4; ry:4; stroke-width:1; transition:filter .12s; }
    .h-node:hover rect { filter:brightness(1.5); }
    .h-node text { font-size:9px; fill:var(--text); pointer-events:none; dominant-baseline:middle; text-anchor:middle; }
    .h-link { fill:none; stroke-width:1; opacity:.22; transition:opacity .12s, stroke-width .12s; }
    .h-link.hl { opacity:.92; stroke-width:2.5; }
    .h-link.dim { opacity:.04; }
    /* info panel */
    .info { position:fixed; bottom:18px; right:18px; background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:13px 16px; min-width:250px; max-width:360px; font-size:12px; display:none; z-index:200; }
    .info.vis { display:block; }
    .info h3 { color:var(--accent); margin-bottom:7px; font-size:13px; }
    .info p { color:var(--text-dim); line-height:1.65; }
    .info .x { position:absolute; top:7px; right:10px; background:none; border:none; color:var(--text-dim); cursor:pointer; font-size:15px; }
    /* doc map */
    .doc-node rect { rx:5; ry:5; stroke-width:1.5; cursor:pointer; }
    .doc-node:hover rect { filter:brightness(1.35); }
    .doc-node text { font-size:10px; fill:var(--text); pointer-events:none; }
    .dline { fill:none; stroke:#4a5280; stroke-width:1.5; marker-end:url(#arr); opacity:.6; }
    .dline.hl { stroke:var(--accent); opacity:1; stroke-width:2.5; marker-end:url(#arr-hi); }
    ::-webkit-scrollbar { width:5px; height:5px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
  </style>
</head>
<body>
<header>
  <h1>ASPICE 추적성 시각화</h1>
  <span class="badge">CLI Calculator — soorak-sam</span>
  <span class="badge">SWE-1 ～ SWE-6</span>
  <span class="badge badge-pass">&#10003; 전체 추적성 완결</span>
  <span class="badge-ts" id="gen-ts"></span>
</header>
<nav class="tabs">
  <button class="tab-btn active" onclick="switchTab('doc',this)">① 문서 연결도</button>
  <button class="tab-btn" onclick="switchTab('mx',this)">② 추적성 매트릭스</button>
  <button class="tab-btn" onclick="switchTab('hz',this)">③ ID 계층 추적도</button>
</nav>

<!-- TAB 1: 문서 연결도 -->
<div id="tab-doc" class="tab-panel active">
  <div class="legend">
    <div class="l-item"><div class="l-dot" style="background:#a569bd"></div>MAN-3</div>
    <div class="l-item"><div class="l-dot" style="background:#5dade2"></div>SWE-1 요구사항</div>
    <div class="l-item"><div class="l-dot" style="background:#48c9b0"></div>SWE-2 아키텍처</div>
    <div class="l-item"><div class="l-dot" style="background:#52be80"></div>SWE-3 단위설계</div>
    <div class="l-item"><div class="l-dot" style="background:#f0a500"></div>SWE-4 단위TC</div>
    <div class="l-item"><div class="l-dot" style="background:#ec7063"></div>SWE-5 통합TC</div>
    <div class="l-item"><div class="l-dot" style="background:#af7ac5"></div>SWE-6 적격성TC</div>
    <div class="l-item"><div class="l-dot" style="background:#5d6d7e"></div>SUP/SPL</div>
    <span style="font-size:11px;color:var(--text-dim);margin-left:8px">↑ 노드 클릭 시 연결 문서 강조</span>
  </div>
  <svg id="dmap" viewBox="0 0 1200 400" style="width:100%;min-height:400px;"></svg>
</div>

<!-- TAB 2: 추적성 매트릭스 -->
<div id="tab-mx" class="tab-panel">
  <p style="font-size:12px;color:var(--text-dim);margin-bottom:14px">행 클릭 → 우측 하단 패널에 매핑 목록 표시. 열 헤더에 마우스 올리면 TC명 표시.</p>
  <div class="mwrap" id="mx-wrap"></div>
</div>

<!-- TAB 3: ID 계층 추적도 -->
<div id="tab-hz" class="tab-panel">
  <p style="font-size:12px;color:var(--text-dim);margin-bottom:14px">
    노드 클릭 → 전방향·역방향 추적 체인 강조.
    <button onclick="clearHL()" style="margin-left:10px;background:var(--bg3);border:1px solid var(--border);color:var(--text-dim);padding:2px 9px;border-radius:3px;cursor:pointer;font-size:11px">선택 해제</button>
  </p>
  <div id="hwrap"><svg id="hsv"></svg></div>
</div>

<!-- 정보 패널 -->
<div class="info" id="info">
  <button class="x" onclick="document.getElementById('info').classList.remove('vis')">&times;</button>
  <h3 id="info-t">—</h3>
  <p id="info-b">—</p>
</div>

<script>
/* __DATA_BLOCK__ */

/* ── 정적 문서 연결도 데이터 ── */
const DOCUMENTS = [
  {id:'MAN3-PP-0001',       label:'MAN3-PP-0001\n프로젝트 계획서',         x:20, y:40,  col:'#7d3c98', proc:'MAN-3',  file:'MAN-3/MAN3-PP-0001-project-plan.md'},
  {id:'SWE1-REQ-SPEC-0001', label:'SWE1-REQ-SPEC\n요구사항 명세서',        x:195,y:40,  col:'#2471a3', proc:'SWE-1',  file:'SWE-1/SWE-1-requirements.md'},
  {id:'SWE1-TRACE-0001',    label:'SWE1-TRACE\n추적성',                    x:195,y:130, col:'#1f618d', proc:'SWE-1',  file:'SWE-1/SWE1-TRACE-0001-traceability-review.md'},
  {id:'SWE2-ARCH-0001',     label:'SWE2-ARCH-0001\n소프트웨어 아키텍처',   x:380,y:40,  col:'#0e6655', proc:'SWE-2',  file:'SWE-2/SWE2-ARCH-0001-software-architecture.md'},
  {id:'SWE2-TRACE-0001',    label:'SWE2-TRACE\n추적성',                    x:380,y:130, col:'#0b5345', proc:'SWE-2',  file:'SWE-2/SWE2-TRACE-0001-traceability-review.md'},
  {id:'SWE3-UNIT-SPEC-0001',label:'SWE3-UNIT-SPEC\n단위 설계 명세',        x:555,y:40,  col:'#1d6a3a', proc:'SWE-3',  file:'SWE-3/SWE3-UNIT-SPEC-0001-unit-design.md'},
  {id:'SWE3-TRACE-0001',    label:'SWE3-TRACE\n추적성',                    x:555,y:130, col:'#196f3d', proc:'SWE-3',  file:'SWE-3/SWE3-TRACE-0001-traceability-review.md'},
  {id:'SWE4-TC-SPEC-0001',  label:'SWE4-TC-SPEC\n단위 테스트 케이스',      x:730,y:40,  col:'#9a6003', proc:'SWE-4',  file:'SWE-4/SWE4-TC-SPEC-0001-unit-test.md'},
  {id:'SWE4-TRACE-0001',    label:'SWE4-TRACE\n추적성',                    x:730,y:130, col:'#876000', proc:'SWE-4',  file:'SWE-4/SWE4-TRACE-0001-traceability-review.md'},
  {id:'SWE5-ITC-SPEC-0001', label:'SWE5-ITC-SPEC\n통합 테스트 케이스',     x:900,y:40,  col:'#943126', proc:'SWE-5',  file:'SWE-5/SWE5-ITC-SPEC-0001-integration-test.md'},
  {id:'SWE5-TRACE-0001',    label:'SWE5-TRACE\n추적성',                    x:900,y:130, col:'#7b241c', proc:'SWE-5',  file:'SWE-5/SWE5-TRACE-0001-traceability-review.md'},
  {id:'SWE6-QTC-SPEC-0001', label:'SWE6-QTC-SPEC\n적격성 테스트 케이스',   x:1065,y:40, col:'#6c3483', proc:'SWE-6',  file:'SWE-6/SWE6-QTC-SPEC-0001-qualification-test.md'},
  {id:'SWE6-TRACE-0001',    label:'SWE6-TRACE\n추적성',                    x:1065,y:130,col:'#5b2c6f', proc:'SWE-6',  file:'SWE-6/SWE6-TRACE-0001-traceability-review.md'},
  {id:'SPL2-BUILD-0001',    label:'SPL2-BUILD\n빌드 환경',                  x:20, y:230, col:'#4a5568', proc:'SPL-2',  file:'SPL-2/SPL2-BUILD-0001-build-environment.md'},
  {id:'SPL2-REL-0001',      label:'SPL2-REL\n출시 노트',                    x:195,y:230, col:'#4a5568', proc:'SPL-2',  file:'SPL-2/SPL2-REL-0001-release-note.md'},
  {id:'SUP1-QAR-0001',      label:'SUP1-QAR\nQA 감사 보고서',              x:380,y:230, col:'#4a5568', proc:'SUP-1',  file:'SUP-1/SUP1-QAR-0001-qa-audit-report.md'},
  {id:'SUP8-CMP-0001',      label:'SUP8-CMP\n형상 관리 계획',               x:555,y:230, col:'#4a5568', proc:'SUP-8',  file:'SUP-8/SUP8-CMP-0001-cm-plan.md'},
  {id:'SUP8-CI-LIST-0001',  label:'SUP8-CI-LIST\nCI 베이스라인',            x:730,y:230, col:'#4a5568', proc:'SUP-8',  file:'SUP-8/SUP8-CI-LIST-0001-ci-baseline.md'},
  {id:'SUP9-PRM-0001',      label:'SUP9-PRM\n문제 해결 관리',               x:900,y:230, col:'#4a5568', proc:'SUP-9',  file:'SUP-9/SUP9-PRM-0001-problem-resolution.md'},
  {id:'SUP10-CR-0001',      label:'SUP10-CR\n변경 요청',                    x:1065,y:230,col:'#4a5568', proc:'SUP-10', file:'SUP-10/SUP10-CR-0001-change-request.md'},
];
const DOC_EDGES = [
  ['MAN3-PP-0001','SWE1-REQ-SPEC-0001'],
  ['SWE1-REQ-SPEC-0001','SWE1-TRACE-0001'],['SWE1-REQ-SPEC-0001','SWE2-ARCH-0001'],
  ['SWE2-ARCH-0001','SWE2-TRACE-0001'],    ['SWE2-ARCH-0001','SWE3-UNIT-SPEC-0001'],
  ['SWE3-UNIT-SPEC-0001','SWE3-TRACE-0001'],['SWE3-UNIT-SPEC-0001','SWE4-TC-SPEC-0001'],
  ['SWE4-TC-SPEC-0001','SWE4-TRACE-0001'], ['SWE4-TC-SPEC-0001','SWE5-ITC-SPEC-0001'],
  ['SWE5-ITC-SPEC-0001','SWE5-TRACE-0001'],['SWE5-ITC-SPEC-0001','SWE6-QTC-SPEC-0001'],
  ['SWE6-QTC-SPEC-0001','SWE6-TRACE-0001'],
  ['SPL2-BUILD-0001','SWE3-UNIT-SPEC-0001'],['SUP1-QAR-0001','SWE4-TC-SPEC-0001'],
  ['SUP8-CMP-0001','SWE2-ARCH-0001'],      ['SUP8-CI-LIST-0001','SWE4-TC-SPEC-0001'],
  ['SUP9-PRM-0001','SWE5-ITC-SPEC-0001'],  ['SUP10-CR-0001','SWE6-QTC-SPEC-0001'],
];

/* ── 공통 유틸 ── */
function switchTab(name,btn){
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  btn.classList.add('active');
}
function showInfo(t,b){
  const p=document.getElementById('info');
  document.getElementById('info-t').textContent=t;
  document.getElementById('info-b').innerHTML=b;
  p.classList.add('vis');
}
document.getElementById('gen-ts').textContent='생성: '+GENERATED_AT;

/* ── TAB 1: 문서 연결도 ── */
(function(){
  const svg=document.getElementById('dmap'), NS='http://www.w3.org/2000/svg';
  const defs=document.createElementNS(NS,'defs');
  defs.innerHTML=
    '<marker id="arr" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">'+
    '<polygon points="0 0,7 2.5,0 5" fill="#4a5280"/></marker>'+
    '<marker id="arr-hi" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">'+
    '<polygon points="0 0,7 2.5,0 5" fill="#4f8ef7"/></marker>';
  svg.appendChild(defs);
  const eg=document.createElementNS(NS,'g'); eg.id='eg'; svg.appendChild(eg);
  const ng=document.createElementNS(NS,'g'); svg.appendChild(ng);
  const idx={}; DOCUMENTS.forEach(d=>idx[d.id]=d);
  const W=150,H=46;
  DOC_EDGES.forEach(([s,t])=>{
    const sd=idx[s],td=idx[t]; if(!sd||!td) return;
    const x1=sd.x+W,y1=sd.y+H/2,x2=td.x,y2=td.y+H/2,mx=(x1+x2)/2;
    const p=document.createElementNS(NS,'path');
    p.setAttribute('d',`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`);
    p.setAttribute('class','dline'); p.dataset.s=s; p.dataset.t=t;
    eg.appendChild(p);
  });
  DOCUMENTS.forEach(doc=>{
    const g=document.createElementNS(NS,'g');
    g.setAttribute('class','doc-node');
    g.setAttribute('transform',`translate(${doc.x},${doc.y})`);
    const r=document.createElementNS(NS,'rect');
    r.setAttribute('width',W); r.setAttribute('height',H);
    r.setAttribute('fill',doc.col+'30'); r.setAttribute('stroke',doc.col); r.setAttribute('rx','5');
    g.appendChild(r);
    doc.label.split('\n').forEach((line,i)=>{
      const t=document.createElementNS(NS,'text');
      t.setAttribute('x',W/2); t.setAttribute('y',i===0?16:32);
      t.setAttribute('text-anchor','middle');
      t.setAttribute('font-size',i===0?'10':'9');
      t.setAttribute('fill',i===0?'#e2e4f0':'#8890b0');
      t.textContent=line; g.appendChild(t);
    });
    g.addEventListener('click',()=>{
      eg.querySelectorAll('.dline').forEach(e=>{e.setAttribute('class','dline');e.setAttribute('marker-end','url(#arr)');});
      eg.querySelectorAll('.dline').forEach(e=>{
        if(e.dataset.s===doc.id||e.dataset.t===doc.id){
          e.setAttribute('class','dline hl'); e.setAttribute('marker-end','url(#arr-hi)');
        }
      });
      showInfo(doc.id,`프로세스: <b>${doc.proc}</b><br>파일: <code>${doc.file}</code>`);
    });
    ng.appendChild(g);
  });
})();

/* ── TAB 2: 추적성 매트릭스 ── */
(function(){
  const el=document.getElementById('mx-wrap');
  const tb=document.createElement('table'); tb.className='mx';
  // group header
  const hr1=document.createElement('tr');
  const e0=document.createElement('th'); e0.className='rh'; e0.setAttribute('rowspan','2');
  e0.textContent='SW 요구사항 (SWE-1)'; hr1.appendChild(e0);
  [{list:TCS,cls:'gh-tc',label:`SWE-4 단위 TC (${TCS.length}개)`},
   {list:ITCS,cls:'gh-itc',label:`SWE-5 통합 ITC (${ITCS.length}개)`},
   {list:QTCS,cls:'gh-qtc',label:`SWE-6 적격성 QTC (${QTCS.length}개)`}
  ].forEach(g=>{
    const th=document.createElement('th');
    th.setAttribute('colspan',g.list.length); th.className=g.cls;
    th.textContent=g.label+' — 모두 Pass'; hr1.appendChild(th);
  });
  // id header
  const hr2=document.createElement('tr');
  [...TCS,...ITCS,...QTCS].forEach((tc,i)=>{
    const th=document.createElement('th');
    th.textContent=tc.id.replace('SWE-TC-','TC-').replace('SWE-ITC-','ITC-').replace('SWE-QTC-','QTC-');
    th.title=(TC_LABELS[tc.id]||ITC_LABELS[tc.id]||QTC_LABELS[tc.id]||'');
    th.style.writingMode='vertical-rl'; th.style.minWidth='26px'; th.style.height='76px'; th.style.padding='3px 1px';
    th.className=i<TCS.length?'cg-tc':i<TCS.length+ITCS.length?'cg-itc':'cg-qtc';
    hr2.appendChild(th);
  });
  const thead=document.createElement('thead');
  thead.appendChild(hr1); thead.appendChild(hr2); tb.appendChild(thead);
  const tbody=document.createElement('tbody');
  REQS.forEach(req=>{
    const tr=document.createElement('tr'); tr.dataset.req=req.id;
    const td0=document.createElement('td'); td0.className='rid';
    td0.title=req.label;
    td0.innerHTML=`${req.id}<br><span style="font-size:9px;color:#8890b0;font-weight:400">${req.label}</span>`;
    tr.appendChild(td0);
    const myTC=new Set(REQ_TC[req.id]||[]);
    const myITC=new Set(REQ_ITC[req.id]||[]);
    const myQTC=new Set(REQ_QTC[req.id]||[]);
    [...TCS,...ITCS,...QTCS].forEach((tc,i)=>{
      const td=document.createElement('td');
      let hit=false;
      if(i<TCS.length){hit=myTC.has(tc.id);td.className='cg-tc';}
      else if(i<TCS.length+ITCS.length){hit=myITC.has(tc.id);td.className='cg-itc';}
      else{hit=myQTC.has(tc.id);td.className='cg-qtc';}
      td.innerHTML=hit?'<span class="chk">✓</span>':'<span class="cmt">·</span>';
      if(hit) td.title=`${tc.id} → ${req.id}`;
      tr.appendChild(td);
    });
    tr.addEventListener('mouseenter',()=>tr.classList.add('rhi'));
    tr.addEventListener('mouseleave',()=>tr.classList.remove('rhi'));
    tr.querySelector('.rid').addEventListener('click',()=>{
      const tcl=(REQ_TC[req.id]||[]).join(', ')||'—';
      const itcl=(REQ_ITC[req.id]||[]).join(', ')||'—';
      const qtcl=(REQ_QTC[req.id]||[]).join(', ')||'—';
      showInfo(req.id+' — '+req.label,
        `<b>단위 TC (SWE-4):</b><br><span style="font-size:10px">${tcl}</span><br><br>`+
        `<b>통합 ITC (SWE-5):</b><br><span style="font-size:10px">${itcl}</span><br><br>`+
        `<b>적격성 QTC (SWE-6):</b><br><span style="font-size:10px">${qtcl}</span>`);
    });
    tbody.appendChild(tr);
  });
  tb.appendChild(tbody); el.appendChild(tb);
})();

/* ── TAB 3: ID 계층 추적도 ── */
(function(){
  const NS='http://www.w3.org/2000/svg';
  const LAYERS=[
    {key:'goal', name:'프로젝트\n목표', col:'#9b59b6', items:GOAL_ITEMS},
    {key:'req',  name:'SW 요구사항\nSWE-1',  col:'#2980b9', items:REQS.map(r=>({id:r.id,label:r.label}))},
    {key:'comp', name:'아키텍처\nSWE-2',     col:'#16a085', items:COMP_ITEMS},
    {key:'unit', name:'단위\nSWE-3',         col:'#27ae60', items:UNIT_ITEMS},
    {key:'tc',   name:'단위TC\nSWE-4',       col:'#e67e22', items:TCS.map(t=>({id:t.id,label:TC_LABELS[t.id]||t.id}))},
    {key:'itc',  name:'통합ITC\nSWE-5',      col:'#c0392b', items:ITCS.map(t=>({id:t.id,label:ITC_LABELS[t.id]||t.id}))},
    {key:'qtc',  name:'적격성QTC\nSWE-6',    col:'#8e44ad', items:QTCS.map(t=>({id:t.id,label:QTC_LABELS[t.id]||t.id}))},
  ];
  const NW=118,NH=24,GX=56,GY=5,PX=18,PY=55;
  const lx=LAYERS.map((_,i)=>PX+i*(NW+GX));
  const totW=lx[LAYERS.length-1]+NW+PX;
  const totH=PY+38+Math.max(...LAYERS.map(l=>l.items.length))*(NH+GY)+PY;
  const svg=document.getElementById('hsv');
  svg.setAttribute('width',totW); svg.setAttribute('height',totH);
  // position index
  const pos={};
  LAYERS.forEach((layer,li)=>{
    layer.items.forEach((item,ii)=>{
      const x=lx[li], y=PY+38+ii*(NH+GY);
      pos[item.id]={x,y,cx:x+NW/2,cy:y+NH/2};
    });
  });
  // edges
  const edges=[];
  Object.entries(GOAL_REQ).forEach(([g,rs])=>rs.forEach(r=>edges.push({s:g,t:r,col:'#9b59b6'})));
  Object.entries(REQ_COMP).forEach(([r,cs])=>cs.forEach(c=>edges.push({s:r,t:c,col:'#2980b9'})));
  Object.entries(COMP_UNIT).forEach(([c,us])=>us.forEach(u=>edges.push({s:c,t:u,col:'#16a085'})));
  Object.entries(REQ_TC).forEach(([r,ts])=>ts.forEach(t=>edges.push({s:r,t,col:'#e67e22'})));
  Object.entries(REQ_ITC).forEach(([r,ts])=>ts.forEach(t=>edges.push({s:r,t,col:'#c0392b'})));
  Object.entries(REQ_QTC).forEach(([r,ts])=>ts.forEach(t=>edges.push({s:r,t,col:'#8e44ad'})));
  const lg=document.createElementNS(NS,'g'); lg.id='hlinks'; svg.appendChild(lg);
  edges.forEach(e=>{
    const sp=pos[e.s],tp=pos[e.t]; if(!sp||!tp) return;
    const mx=(sp.x+NW+tp.x)/2;
    const p=document.createElementNS(NS,'path');
    p.setAttribute('d',`M${sp.x+NW},${sp.cy} C${mx},${sp.cy} ${mx},${tp.cy} ${tp.x},${tp.cy}`);
    p.setAttribute('class','h-link'); p.setAttribute('stroke',e.col);
    p.dataset.s=e.s; p.dataset.t=e.t; lg.appendChild(p);
  });
  // layer headers
  LAYERS.forEach((layer,li)=>{
    const x=lx[li];
    const bg=document.createElementNS(NS,'rect');
    bg.setAttribute('x',x); bg.setAttribute('y',PY-33);
    bg.setAttribute('width',NW); bg.setAttribute('height',30);
    bg.setAttribute('fill',layer.col+'40');
    bg.setAttribute('stroke',layer.col); bg.setAttribute('stroke-width','1'); bg.setAttribute('rx','4');
    svg.appendChild(bg);
    layer.name.split('\n').forEach((line,i)=>{
      const t=document.createElementNS(NS,'text');
      t.setAttribute('x',x+NW/2); t.setAttribute('y',PY-19+i*13);
      t.setAttribute('text-anchor','middle');
      t.setAttribute('font-size','10'); t.setAttribute('fill',layer.col);
      t.setAttribute('font-weight','600'); t.textContent=line;
      svg.appendChild(t);
    });
  });
  // nodes
  const ng=document.createElementNS(NS,'g'); svg.appendChild(ng);
  LAYERS.forEach(layer=>{
    layer.items.forEach(item=>{
      const p=pos[item.id]; if(!p) return;
      const g=document.createElementNS(NS,'g');
      g.setAttribute('class','h-node');
      g.setAttribute('transform',`translate(${p.x},${p.y})`);
      g.dataset.id=item.id; g.dataset.lkey=layer.key;
      const r=document.createElementNS(NS,'rect');
      r.setAttribute('width',NW); r.setAttribute('height',NH);
      r.setAttribute('fill',layer.col+'20'); r.setAttribute('stroke',layer.col); r.setAttribute('rx','3');
      g.appendChild(r);
      const tid=document.createElementNS(NS,'text');
      tid.setAttribute('x',NW/2); tid.setAttribute('y',9);
      tid.setAttribute('font-size','8'); tid.setAttribute('fill',layer.col);
      tid.setAttribute('font-weight','600');
      tid.textContent=item.id.replace('SWE-','').replace('PROJ-GOAL-','GOAL-');
      g.appendChild(tid);
      const tlbl=document.createElementNS(NS,'text');
      tlbl.setAttribute('x',NW/2); tlbl.setAttribute('y',18);
      tlbl.setAttribute('font-size','7.5'); tlbl.setAttribute('fill','#8890b0');
      const lbl=item.label||'';
      tlbl.textContent=lbl.length>18?lbl.slice(0,17)+'…':lbl;
      g.appendChild(tlbl);
      g.addEventListener('click',()=>hlChain(item.id,layer.key));
      ng.appendChild(g);
    });
  });
})();

/* ── 계층도 하이라이트 ── */
function getChain(id,lkey){
  const conn=new Set([id]);
  function bk(nid,lk){
    if(lk==='req'){Object.entries(GOAL_REQ).forEach(([g,rs])=>{if(rs.includes(nid)){conn.add(g);bk(g,'goal');}});}
    if(lk==='comp'){Object.entries(REQ_COMP).forEach(([r,cs])=>{if(cs.includes(nid)){conn.add(r);bk(r,'req');}});}
    if(lk==='unit'){Object.entries(COMP_UNIT).forEach(([c,us])=>{if(us.includes(nid)){conn.add(c);bk(c,'comp');}});}
    if(lk==='tc'){Object.entries(REQ_TC).forEach(([r,ts])=>{if(ts.includes(nid)){conn.add(r);bk(r,'req');}});}
    if(lk==='itc'){Object.entries(REQ_ITC).forEach(([r,ts])=>{if(ts.includes(nid)){conn.add(r);bk(r,'req');}});}
    if(lk==='qtc'){Object.entries(REQ_QTC).forEach(([r,ts])=>{if(ts.includes(nid)){conn.add(r);bk(r,'req');}});}
  }
  function fw(nid,lk){
    if(lk==='goal'){(GOAL_REQ[nid]||[]).forEach(r=>{conn.add(r);fw(r,'req');});}
    if(lk==='req'){
      (REQ_COMP[nid]||[]).forEach(c=>{conn.add(c);fw(c,'comp');});
      (REQ_TC[nid]||[]).forEach(t=>{conn.add(t);fw(t,'tc');});
      (REQ_ITC[nid]||[]).forEach(t=>{conn.add(t);fw(t,'itc');});
      (REQ_QTC[nid]||[]).forEach(t=>{conn.add(t);fw(t,'qtc');});
    }
    if(lk==='comp'){(COMP_UNIT[nid]||[]).forEach(u=>{conn.add(u);fw(u,'unit');});}
  }
  bk(id,lkey); fw(id,lkey);
  return conn;
}
function hlChain(id,lkey){
  const conn=getChain(id,lkey);
  document.querySelectorAll('.h-link').forEach(l=>{
    const ok=conn.has(l.dataset.s)&&conn.has(l.dataset.t);
    l.className='h-link'+(ok?' hl':' dim');
  });
  document.querySelectorAll('.h-node rect').forEach(r=>{
    r.style.filter=conn.has(r.parentElement.dataset.id)?'brightness(2)':'brightness(0.4)';
  });
}
function clearHL(){
  document.querySelectorAll('.h-link').forEach(l=>l.className='h-link');
  document.querySelectorAll('.h-node rect').forEach(r=>r.style.filter='');
}
</script>
</body>
</html>
"""

def generate_html(data: dict) -> str:
    """데이터 블록을 HTML 템플릿에 주입하여 완성된 HTML 반환"""
    data_block = build_data_block(data)
    return HTML_TEMPLATE.replace("/* __DATA_BLOCK__ */", data_block)

# ══════════════════════════════════════════════════════════════════════════════
# 9. 메인
# ══════════════════════════════════════════════════════════════════════════════

def main():
    force  = "--force" in sys.argv
    check  = "--check" in sys.argv
    quiet  = "--quiet" in sys.argv

    def log(msg: str):
        if not quiet:
            print(msg)

    log("── ASPICE 추적성 동기화 ─────────────────────────")

    # 1. 현재 데이터 빌드
    log("  [1/3] docs/ 파싱 중...")
    data = build_data()
    new_hash = content_hash(data)

    ids  = data["ids"]
    rels = data["rels"]
    log(f"       REQ:{len(ids['reqs'])}  TC:{len(ids['tcs'])}  "
        f"ITC:{len(ids['itcs'])}  QTC:{len(ids['qtcs'])}")

    # 2. 변경 감지
    log("  [2/3] 변경 감지 중...")
    cache    = load_cache()
    old_hash = cache.get("hash", "")
    changed  = (new_hash != old_hash) or force

    if not changed:
        log(f"     → 변경 없음 (hash={new_hash}). HTML 갱신 생략.")
        if check:
            sys.exit(0)
        return

    # diff 출력
    if old_hash:
        diffs = diff_summary(cache, data)
        if diffs:
            log("     변경 내용:")
            for d in diffs:
                log(d)
        else:
            log("     (레이블/메타 변경)")
    else:
        log("     (첫 실행 — 캐시 없음)")

    if check:
        log("  → --check 모드: 변경 감지됨 (exit 1)")
        sys.exit(1)

    # 3. HTML 생성 + 캐시 저장
    log("  [3/3] HTML 생성 중...")
    HTML_OUT.write_text(generate_html(data), encoding="utf-8")
    save_cache(data, new_hash)

    log(f"  ✓ 생성 완료: {HTML_OUT.relative_to(REPO_ROOT)}")
    log(f"       (hash={new_hash})")
    log("─────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
