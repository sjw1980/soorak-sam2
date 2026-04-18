"""
ASPICE Workflow HTML Generator
Reads 260414_aspice_workflow.md and 260414_aspice_wp_overview.md
and generates a single-page interactive HTML with flow diagrams and toggleable WP details.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
WORKFLOW_MD = BASE_DIR / "docs" / "0_cases" / "single" / "260414_aspice_workflow.md"
WP_MD = BASE_DIR / "docs" / "0_cases" / "single" / "260414_aspice_wp_overview.md"
OUTPUT_HTML = BASE_DIR / "output" / "260414_aspice_overview.html"


# ══════════════════════════════════════════════════════════════════════════════
# 1. WP 상세 정보 파싱  (260414_aspice_wp_overview.md)
# ══════════════════════════════════════════════════════════════════════════════


def parse_wp_details(path: Path) -> dict:
    """
    Returns  {  "WP.04-04": {"name": "소프트웨어 아키텍처 설계서", "bullets": [...]} }
    """
    text = path.read_text(encoding="utf-8")
    wp_data: dict = {}

    # #### 04-04 소프트웨어 아키텍처 설계서  형태의 헤더를 기준으로 분할
    pattern = re.compile(
        r"####\s+(\d{2}-\d{2}[\*]?)\s+(.+?)\n(.*?)(?=\n####|\n###|\Z)",
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        raw_id = m.group(1).replace("*", "").strip()
        name = m.group(2).strip()
        body = m.group(3)

        wp_id = f"WP.{raw_id}"

        # 불릿 항목 추출 (- 로 시작하는 줄)
        bullets = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                bullets.append(stripped[2:])
            elif stripped.startswith("-"):
                bullets.append(stripped[1:].strip())

        wp_data[wp_id] = {"name": name, "bullets": bullets}

    return wp_data


# ══════════════════════════════════════════════════════════════════════════════
# 2. 워크플로우 파싱  (260414_aspice_workflow.md)
# ══════════════════════════════════════════════════════════════════════════════


def parse_mermaid_phases(mermaid: str) -> tuple:
    """
    Mermaid 블록에서 파싱:
    1. phases: [{"id": "Phase.1", "label": "Phase.1: 계획 및 전략"}, ...]
    2. phase_bp_map: {"Phase.1": {"Phase.1.1": [...bpids], ...}, "Phase.2": [...bpids], ...}
       Phase.1 은 서브그룹(Phase.1.1~1.4) 구조, 나머지는 flat list
    """
    phases = []
    phase_pattern = re.compile(r'subgraph\s+(Phase\.\d+)\s*\["?([^"\]]+)"?\]')
    for m in phase_pattern.finditer(mermaid):
        phases.append({"id": m.group(1), "label": m.group(2).strip()})

    phase_bp_map: dict = {}

    # Phase.1 – 서브그룹 구조
    sub_pattern = re.compile(r"subgraph\s+(Phase\.\d+\.\d+)\s*\n(.*?)end", re.DOTALL)
    p1_groups: dict = {}
    for m in sub_pattern.finditer(mermaid):
        sub_id = m.group(1)
        body = m.group(2)
        raw_nodes = re.findall(r"((?:\w+\.)+BP\w+)(?:\.\w+)?\[", body)
        clean = []
        for n in raw_nodes:
            base = re.match(r"(\w+\.\w+\.BP\d+)", n)
            if base and base.group(1) not in clean:
                clean.append(base.group(1))
        p1_groups[sub_id] = clean
    if p1_groups:
        phase_bp_map["Phase.1"] = p1_groups  # dict of subgroup → bp list

    # Phase.2, 4, 5, 6 – flat
    for phase_name in ["Phase.2", "Phase.4", "Phase.5", "Phase.6"]:
        escaped = re.escape(phase_name)
        pat = r'subgraph\s+' + escaped + r'\s*\[.*?\]\s*\n(.*?)end'
        m2 = re.search(pat, mermaid, re.DOTALL)
        if m2:
            body = m2.group(1)
            raw_nodes = re.findall(r"((?:\w+\.)+BP\w+)(?:\.\w+)?\[", body)
            clean = []
            for n in raw_nodes:
                base = re.match(r"(\w+\.\w+\.BP\d+)", n)
                if base and base.group(1) not in clean:
                    clean.append(base.group(1))
            phase_bp_map[phase_name] = clean

    # Phase.3 – SWE 서브그룹 구조
    swe_groups: dict = {}
    for swe in ["SWE.1", "SWE.2", "SWE.3", "SWE.4", "SWE.5", "SWE.6"]:
        escaped = re.escape(swe)
        pat = r'subgraph\s+' + escaped + r'\s*\[.*?\]\s*\n(.*?)end'
        m3 = re.search(pat, mermaid, re.DOTALL)
        if m3:
            body = m3.group(1)
            raw_nodes = re.findall(r"((?:\w+\.)+BP\w+)(?:\.\w+)?\[", body)
            clean = []
            for n in raw_nodes:
                base = re.match(r"(\w+\.\w+\.BP\d+)", n)
                if base and base.group(1) not in clean:
                    clean.append(base.group(1))
            swe_groups[swe] = clean
    if swe_groups:
        phase_bp_map["Phase.3"] = swe_groups

    return phases, phase_bp_map


def parse_workflow(path: Path):
    """
    Returns:
      phases: [{"id": "Phase.1", "label": "..."}, ...]
      phase_bp_map: {"Phase.1": {"Phase.1.1": [...], ...}, "Phase.2": [...], ...}
      bp_detail_map: {"MAN.3.BP1": {"desc": "...", "notes": [...], "wps_by_outcome": [...]}, ...}
    """
    text = path.read_text(encoding="utf-8")

    # Mermaid 블록에서 Phase 구조 파싱
    mermaid_m = re.search(r"```mermaid(.*?)```", text, re.DOTALL)
    mermaid = mermaid_m.group(1) if mermaid_m else ""

    phases, phase_bp_map = parse_mermaid_phases(mermaid)

    # H1 섹션별 분할 (# MAN.3 ..., # SWE.1 ... 등)
    sections_raw = re.split(r"\n# ", text)
    # bp_detail_map: bp_id → {desc, notes, outcomes:[{outcome, wps:[]}]}
    bp_detail_map: dict = {}

    for raw in sections_raw[1:]:  # 첫 번째는 제목(mermaid 포함) 스킵
        lines = raw.strip().splitlines()
        if not lines:
            continue

        # BP 테이블 파싱
        bps_in_section: list = []
        current_bp = None
        in_table = False
        for line in lines[1:]:
            if re.match(r"\|\s*PROCESS", line, re.IGNORECASE):
                in_table = True
                continue
            if re.match(r"\|\s*[-|]+\s*$", line):
                continue
            if in_table and line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2:
                    bp_id = cells[0].strip()
                    desc = cells[1].strip()
                    # WP 컬럼(3번째)에 '성과 N' 형태면 desc에서 꺼내기
                    # 단순히 bp 행인지 note 행인지 구분
                    if bp_id and bp_id != "-" and not bp_id.startswith("-"):
                        current_bp = {"id": bp_id, "desc": desc, "notes": []}
                        bps_in_section.append(current_bp)
                        bp_detail_map[bp_id] = current_bp
                    elif bp_id == "-" and current_bp:
                        if desc and not desc.startswith("비고"):
                            current_bp["notes"].append(desc)
            elif in_table and not line.startswith("|"):
                in_table = False

        # 작업 산출물 테이블 파싱 → 성과별 WP 목록 수집
        # 이후 bp에 'outcomes' 매핑은 BP의 WP 컬럼(테이블 3번째 컬럼) 기준으로 역매핑
        outcomes: list = []
        in_wp_table = False
        for line in lines[1:]:
            stripped = line.strip()
            if re.match(r"\|\s*성과\s*\|.*산출물", stripped):
                in_wp_table = True
                continue
            if re.match(r"\|\s*[-: |]+\s*$", stripped):
                continue
            if in_wp_table and stripped.startswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 2:
                    outcome = cells[0].strip()
                    wps_raw = cells[1].strip()
                    if re.match(r"성과\s*\d+", outcome):
                        wp_ids = [
                            w.strip()
                            for w in re.split(r"\s*/\s*", wps_raw)
                            if w.strip()
                        ]
                        outcomes.append({"outcome": outcome, "wps": wp_ids})
            elif in_wp_table and not stripped.startswith("|"):
                in_wp_table = False

        # BP WP 컬럼 파싱 (BP 테이블의 3번째 컬럼 '성과 N, M' 형태)
        # → bp_id 별로 관련 성과 번호 수집 → 그 성과의 WP를 연결
        bp_outcome_map: dict = {}  # bp_id → set of outcome labels
        in_bp_table2 = False
        current_bp2 = None
        for line in lines[1:]:
            if re.match(r"\|\s*PROCESS", line, re.IGNORECASE):
                in_bp_table2 = True
                continue
            if re.match(r"\|\s*[-|]+\s*$", line):
                continue
            if in_bp_table2 and line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 3:
                    bp_id = cells[0].strip()
                    wpc = cells[2].strip()  # 3번째 컬럼: "성과 1, 5, 7" 등
                    if bp_id and bp_id != "-" and not bp_id.startswith("-"):
                        current_bp2 = bp_id
                        if wpc:
                            nums = re.findall(r"\d+", wpc)
                            bp_outcome_map.setdefault(bp_id, set()).update(
                                f"성과 {n}" for n in nums
                            )
                    elif bp_id == "-" and current_bp2:
                        if wpc:
                            nums = re.findall(r"\d+", wpc)
                            bp_outcome_map.setdefault(current_bp2, set()).update(
                                f"성과 {n}" for n in nums
                            )
            elif in_bp_table2 and not line.startswith("|"):
                in_bp_table2 = False

        # outcomes lookup
        outcome_lookup = {oc["outcome"]: oc["wps"] for oc in outcomes}

        # BP detail에 wps 연결
        for bp in bps_in_section:
            bp_id = bp["id"]
            related_outcomes = sorted(bp_outcome_map.get(bp_id, set()))
            bp_wps: list = []
            seen = set()
            for oc_label in related_outcomes:
                for wp in outcome_lookup.get(oc_label, []):
                    if wp not in seen:
                        bp_wps.append(wp)
                        seen.add(wp)
            bp["wps"] = bp_wps
            bp["outcome_labels"] = related_outcomes

    return phases, phase_bp_map, bp_detail_map


# ══════════════════════════════════════════════════════════════════════════════
# 3. Helper: BP 상세 추출
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# 4. HTML 생성
# ══════════════════════════════════════════════════════════════════════════════


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_wp_item(wp_id: str, card_uid: str, wp_details: dict) -> str:
    """오른쪽 패널의 WP 아이템 (클릭 시 WP Flow 탭으로 이동)"""
    info = wp_details.get(wp_id, {})
    name = info.get("name", wp_id)
    wp_uid = re.sub(r"[^a-zA-Z0-9]", "_", wp_id)
    item_id = f"wi-{card_uid}_{wp_uid}"
    return (
        f'<div class="wp-item" id="{item_id}" onclick="jumpToWp(\'{wp_uid}\')">'
        f'<span class="wi-id">{esc(wp_id)}</span>'
        f'<span class="wi-name">{esc(name)}</span>'
        f'<span class="wi-link">&#8599;</span>'
        f'</div>'
    )


def render_merged_split_card(
    sub_groups: dict, bp_detail_map: dict, wp_details: dict
) -> str:
    """Phase.1 전용: 1.1~1.4 서브그룹을 하나의 카드로 합쳐서 렌더링.
    서브그룹 경계(마지막 BP → 다음 그룹 첫 BP)에는 크로스-그룹 화살표 표시."""
    card_uid = "Phase_1_merged"

    # 모든 WP 수집 (순서 유지, 중복 제거)
    all_wps: list = []
    seen_wps: set = set()
    for sub_id, bp_ids in sub_groups.items():
        for bp_id in bp_ids:
            for wp in bp_detail_map.get(bp_id, {}).get("wps", []):
                if wp not in seen_wps:
                    all_wps.append(wp)
                    seen_wps.add(wp)

    # ── 왼쪽: BP 수직 플로우 (서브그룹 레이블 포함) ──
    # 아이템 리스트: ('label', sub_id) | ('bp', bp_id)
    items: list = []
    for sub_id, bp_ids in sub_groups.items():
        items.append(("label", sub_id))
        for bp_id in bp_ids:
            items.append(("bp", bp_id))

    left_html_parts = []
    for k, (itype, ivalue) in enumerate(items):
        if itype == "label":
            left_html_parts.append(
                f'<div class="bp-subgroup-label">{esc(ivalue)}</div>'
            )
        else:  # bp
            bp_id = ivalue
            info = bp_detail_map.get(bp_id, {})
            desc = info.get("desc", "")
            notes = info.get("notes", [])
            bp_uid = re.sub(r"[^a-zA-Z0-9]", "_", bp_id)
            note_attr = f' title="{esc(" | ".join(notes))}"' if notes else ""
            note_icon = '<span class="bp-note-icon">&#9432;</span>' if notes else ""
            left_html_parts.append(
                f'<div class="bp-vbox" id="bpv-{card_uid}_{bp_uid}" data-bp-id="{esc(bp_id)}"{note_attr}>'
                f'<span class="bp-id">{esc(bp_id)}</span>'
                f'<span class="bp-desc">{esc(desc)}</span>'
                f'{note_icon}'
                f'</div>'
            )
            # 다음 아이템에 따라 화살표 종류 결정
            if k + 1 < len(items):
                next_type = items[k + 1][0]
                if next_type == "label":
                    # 서브그룹 경계 → 크로스-그룹 화살표
                    left_html_parts.append('<div class="bp-cross-arrow">&#8595;</div>')
                else:
                    # 같은 그룹 내 일반 화살표
                    left_html_parts.append('<div class="bp-down-arrow">&#8595;</div>')

    left_html = "".join(left_html_parts)

    # ── 오른쪽: WP 아이템 ──
    right_html = "".join(render_wp_item(wp, card_uid, wp_details) for wp in all_wps)
    if not right_html:
        right_html = '<p class="no-wp">산출물 없음</p>'

    # ── 연결선 데이터 ──
    conns = []
    for sub_id, bp_ids in sub_groups.items():
        for bp_id in bp_ids:
            bp_uid = re.sub(r"[^a-zA-Z0-9]", "_", bp_id)
            bp_key = f"bpv-{card_uid}_{bp_uid}"
            wps = bp_detail_map.get(bp_id, {}).get("wps", [])
            wp_keys = [
                f"wi-{card_uid}_{re.sub(r'[^a-zA-Z0-9]', '_', wp)}" for wp in wps
            ]
            if wp_keys:
                conns.append([bp_key, wp_keys])
    data_conns = json.dumps(conns, ensure_ascii=False).replace("'", "&#39;")

    return (
        f'<div class="split-card" id="card-{card_uid}" data-conns=\'{data_conns}\'>'
        f'<div class="split-left" id="sleft-{card_uid}">'
        f'<div class="bp-flow-v">{left_html}</div>'
        f'</div>'
        f'<svg class="conn-svg" id="svg-{card_uid}"></svg>'
        f'<div class="split-right" id="sright-{card_uid}">'
        f'<div class="split-right-header">작업 산출물 (WP)</div>'
        f'{right_html}'
        f'</div>'
        f'</div>'
    )


def render_split_card(
    sub_id: str, bp_ids: list, bp_detail_map: dict, wp_details: dict
) -> str:
    """좌(BP 수직 플로우) + 우(WP 목록) 2-컬럼 카드 + SVG 연결선"""
    card_uid = re.sub(r"[^a-zA-Z0-9]", "_", sub_id)

    # 이 그룹의 WP 목록 (순서 유지, 중복 제거)
    all_wps: list = []
    seen_wps: set = set()
    for bp_id in bp_ids:
        for wp in bp_detail_map.get(bp_id, {}).get("wps", []):
            if wp not in seen_wps:
                all_wps.append(wp)
                seen_wps.add(wp)

    # ── 왼쪽: BP 수직 플로우 ──
    left_items = []
    for bp_id in bp_ids:
        info = bp_detail_map.get(bp_id, {})
        desc = info.get("desc", "")
        notes = info.get("notes", [])
        bp_uid = re.sub(r"[^a-zA-Z0-9]", "_", bp_id)
        note_attr = f' title="{esc(" | ".join(notes))}"' if notes else ""
        note_icon = '<span class="bp-note-icon">&#9432;</span>' if notes else ""
        left_items.append(
            f'<div class="bp-vbox" id="bpv-{card_uid}_{bp_uid}" data-bp-id="{esc(bp_id)}"{note_attr}>'
            f'<span class="bp-id">{esc(bp_id)}</span>'
            f'<span class="bp-desc">{esc(desc)}</span>'
            f'{note_icon}'
            f'</div>'
        )
    left_html = '<div class="bp-down-arrow">&#8595;</div>'.join(left_items)

    # ── 오른쪽: WP 아이템 ──
    right_html = "".join(render_wp_item(wp, card_uid, wp_details) for wp in all_wps)
    if not right_html:
        right_html = '<p class="no-wp">산출물 없음</p>'

    # ── 연결선 데이터 (JSON → data attribute) ──
    conns = []
    for bp_id in bp_ids:
        bp_uid = re.sub(r"[^a-zA-Z0-9]", "_", bp_id)
        bp_key = f"bpv-{card_uid}_{bp_uid}"
        wps = bp_detail_map.get(bp_id, {}).get("wps", [])
        wp_keys = [f"wi-{card_uid}_{re.sub(r'[^a-zA-Z0-9]', '_', wp)}" for wp in wps]
        if wp_keys:
            conns.append([bp_key, wp_keys])
    data_conns = json.dumps(conns, ensure_ascii=False).replace("'", "&#39;")

    return (
        f'<div class="split-card" id="card-{card_uid}" data-conns=\'{data_conns}\'>'
        f'<div class="split-left" id="sleft-{card_uid}">'
        f'<div class="bp-flow-v">{left_html}</div>'
        f'</div>'
        f'<svg class="conn-svg" id="svg-{card_uid}"></svg>'
        f'<div class="split-right" id="sright-{card_uid}">'
        f'<div class="split-right-header">작업 산출물 (WP)</div>'
        f'{right_html}'
        f'</div>'
        f'</div>'
    )


def render_phase_block(
    phase_id: str,
    phase_label: str,
    phase_bp_map: dict,
    bp_detail_map: dict,
    wp_details: dict,
) -> str:
    short = phase_id.split(".")[1] if "." in phase_id else phase_id
    color_class = f"phase-color-{short}"
    bp_data = phase_bp_map.get(phase_id, {})

    if isinstance(bp_data, dict):
        # Phase.1: 서브그룹(1.1~1.4)을 하나로 합쳐서 렌더링
        if phase_id == "Phase.1":
            merged = render_merged_split_card(bp_data, bp_detail_map, wp_details)
            cards_html = (
                f'<div class="process-card" id="proc-Phase_1_merged">'
                f'<div class="process-body" id="body-Phase_1_merged">'
                f'{merged}'
                f'</div>'
                f'</div>'
            )
        else:
            cards_html = ""
            for sub_id, bp_ids in bp_data.items():
                sub_uid = re.sub(r"[^a-zA-Z0-9]", "_", sub_id)
                split = render_split_card(sub_id, bp_ids, bp_detail_map, wp_details)
                cards_html += (
                    f'<div class="process-card" id="proc-{sub_uid}">'
                    f'<div class="process-title" onclick="toggleCard(\'{sub_uid}\')" >'
                    f'<span class="process-name">{esc(sub_id)}</span>'
                    f'<span class="toggle-icon">&#9660;</span>'
                    f'</div>'
                    f'<div class="process-body" id="body-{sub_uid}">'
                    f'{split}'
                    f'</div>'
                    f'</div>'
                )
    elif isinstance(bp_data, list):
        phase_uid = re.sub(r"[^a-zA-Z0-9]", "_", phase_id)
        split = render_split_card(phase_id, bp_data, bp_detail_map, wp_details)
        cards_html = (
            f'<div class="process-card" id="proc-{phase_uid}">'
            f'<div class="process-body" id="body-{phase_uid}">'
            f'{split}'
            f'</div>'
            f'</div>'
        )
    else:
        cards_html = "<p class='no-process'>관련 프로세스 정보 없음</p>"

    return (
        f'<div class="phase-block {color_class}">'
        f'<div class="phase-header" onclick="togglePhase(\'phase{short}\')" >'
        f'<span class="phase-num">Phase {short}</span>'
        f'<span class="phase-label">{esc(phase_label)}</span>'
        f'<span class="phase-toggle-icon">&#9660;</span>'
        f'</div>'
        f'<div class="phase-body" id="phase{short}">'
        f'{cards_html}'
        f'</div>'
        f'</div>'
    )


def render_phase_flow(phases: list) -> str:
    """상단 Phase 흐름도 렌더링"""
    items = []
    for ph in phases:
        short = ph["id"].replace("Phase.", "")
        label = ph["label"]
        # Phase.5, Phase.6 은 피드백 루프
        cls = "phase-flow-item"
        if short in ("5", "6"):
            cls += " phase-flow-feedback"
        items.append(
            f'<div class="{cls}" onclick="scrollToPhase(\'{short}\')">'
            f'<div class="pf-num">Phase {short}</div>'
            f'<div class="pf-label">{esc(label)}</div>'
            f'</div>'
        )

    main_flow = items[:4]
    feedback_flow = items[4:]

    main_html = '<div class="pf-arrow">▶</div>'.join(main_flow)
    fb_html = (
        '<div class="pf-arrow pf-arrow-fb">▶</div>'.join(feedback_flow)
        if feedback_flow
        else ""
    )
    fb_section = (
        f'<div class="phase-flow-feedback-row">{fb_html}</div>' if fb_html else ""
    )

    return f"""
<div class="phase-flow-container">
  <div class="phase-flow-main">{main_html}</div>
  {fb_section}
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# 5. WP Flow 탭 렌더링
# ══════════════════════════════════════════════════════════════════════════════

_WP_CAT_NAMES = {
    "01": "01. 형상 항목 / 소프트웨어 아이템",
    "04": "04. 설계",
    "06": "06. 사용자 문서화",
    "08": "08. 계획서 / 시험 명세",
    "11": "11. 제품",
    "13": "13. 기록",
    "14": "14. 등록",
    "15": "15. 보고서",
    "16": "16. 저장소",
    "17": "17. 요구사항 명세서",
    "18": "18. 기준 / 표준",
    "19": "19. 전략",
}

_BP_COLORS = {
    "MAN.3": ("#1557b0", "#e8f0fe"),
    "SWE.1": ("#137333", "#e6f4ea"),
    "SWE.2": ("#00796b", "#e0f2f1"),
    "SWE.3": ("#e65100", "#fff3e0"),
    "SWE.4": ("#b71c1c", "#ffebee"),
    "SWE.5": ("#6a1b9a", "#f3e5f5"),
    "SWE.6": ("#006064", "#e0f7fa"),
    "SUP.1": ("#bf360c", "#fbe9e7"),
    "SUP.8": ("#4e342e", "#efebe9"),
    "SUP.9": ("#37474f", "#eceff1"),
    "SUP.10": ("#4e342e", "#fce4ec"),
}


def _bp_group(bp_id: str) -> str:
    parts = bp_id.split(".")
    return f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "other"


def render_wp_flow_tab(bp_detail_map: dict, wp_details: dict) -> str:
    """WP Flow 탭: WP 기준으로 관련 BP 연결 렌더링"""
    # 역매핑: wp_id → [bp_ids]
    wp_bp_map: dict = {}
    for bp_id, info in bp_detail_map.items():
        for wp in info.get("wps", []):
            wp_bp_map.setdefault(wp, []).append(bp_id)
    for wp in wp_bp_map:
        wp_bp_map[wp] = sorted(wp_bp_map[wp])

    # 카테고리별 그룹화
    categories: dict = defaultdict(list)
    for wp_id in sorted(wp_bp_map.keys()):
        cat = wp_id.split(".")[1].split("-")[0]  # "WP.08-12" → "08"
        categories[cat].append(wp_id)

    blocks = ""
    for cat in sorted(categories.keys()):
        cat_label = _WP_CAT_NAMES.get(cat, f"{cat}. 기타")
        cat_uid = f"wfcat_{cat}"

        rows_html = ""
        for wp_id in categories[cat]:
            wp_uid = re.sub(r"[^a-zA-Z0-9]", "_", wp_id)
            info = wp_details.get(wp_id, {})
            name = info.get("name", wp_id)
            bullets = info.get("bullets", [])
            bp_ids = wp_bp_map[wp_id]

            detail_id = f"wfd_{wp_uid}"
            bullets_html = (
                "".join(f"<li>{esc(b)}</li>" for b in bullets)
                if bullets
                else "<li>(내용 없음)</li>"
            )

            chips = ""
            for bp_id in bp_ids:
                grp = _bp_group(bp_id)
                fg, bg = _BP_COLORS.get(grp, ("#5f6368", "#f1f3f4"))
                safe_id = bp_id.replace("'", "\\'")
                chips += (
                    f'<span class="wf-bp-chip" '
                    f'style="color:{fg};background:{bg};border:1px solid {fg}30;cursor:pointer" '
                    f'onclick="jumpToBp(\'{safe_id}\')" '
                    f'title="Workflow에서 보기">'
                    f'{esc(bp_id)}</span>'
                )

            rows_html += (
                f'<div class="wf-row">'
                f'<div class="wf-wp-side">'
                f'<div class="wf-wp-card" onclick="toggleWfDetail(\'{detail_id}\')">'
                f'<span class="wf-wp-id">{esc(wp_id)}</span>'
                f'<span class="wf-wp-name">{esc(name)}</span>'
                f'<span class="wf-wp-arr">&#9660;</span>'
                f'</div>'
                f'<div class="wf-wp-detail" id="{detail_id}"><ul>{bullets_html}</ul></div>'
                f'</div>'
                f'<div class="wf-conn">&#8594;</div>'
                f'<div class="wf-bp-side">{chips}</div>'
                f'</div>'
            )

        blocks += (
            f'<div class="wf-category" id="wfc_{cat}">'
            f'<div class="wf-cat-header" onclick="toggleWfCat(\'{cat_uid}\')">'
            f'<span class="wf-cat-title">{esc(cat_label)}</span>'
            f'<span class="wf-cat-toggle">&#9660;</span>'
            f'</div>'
            f'<div class="wf-cat-body" id="{cat_uid}">{rows_html}</div>'
            f'</div>'
        )

    return f'<div class="wf-wrapper">{blocks}</div>'


# ══════════════════════════════════════════════════════════════════════════════
# 6. 전체 HTML 조립
# ══════════════════════════════════════════════════════════════════════════════

CSS = """
:root {
  --c1: #1a73e8; --c1l: #e8f0fe;
  --c2: #0f9d58; --c2l: #e6f4ea;
  --c3: #f4b400; --c3l: #fef9e3;
  --c4: #db4437; --c4l: #fce8e6;
  --c5: #ab47bc; --c5l: #f3e5f5;
  --c6: #00acc1; --c6l: #e0f7fa;
  --gray: #5f6368; --light: #f8f9fa; --border: #dadce0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Noto Sans KR', 'Segoe UI', sans-serif; background: #f1f3f4; color: #202124; }
h1.page-title { text-align:center; padding:24px 16px 8px; font-size:22px; color:#202124; }
.subtitle { text-align:center; color:var(--gray); font-size:13px; margin-bottom:20px; }

/* ── Phase Flow 다이어그램 ── */
.phase-flow-container { max-width:1100px; margin:0 auto 28px; padding:0 16px; }
.phase-flow-main, .phase-flow-feedback-row {
  display:flex; align-items:center; gap:0; flex-wrap:wrap; justify-content:center;
}
.phase-flow-feedback-row { margin-top:10px; }
.phase-flow-item {
  background:#fff; border:2px solid var(--border); border-radius:10px;
  padding:10px 14px; cursor:pointer; min-width:160px; text-align:center;
  transition:box-shadow .2s, border-color .2s;
}
.phase-flow-item:hover { box-shadow:0 4px 16px rgba(0,0,0,.14); border-color:var(--c1); }
.phase-flow-feedback { border-style:dashed; background:#fafafa; }
.pf-num { font-size:11px; font-weight:700; color:var(--c1); margin-bottom:4px; letter-spacing:.5px; }
.pf-label { font-size:12px; color:#3c4043; line-height:1.4; }
.pf-arrow { font-size:20px; color:var(--border); padding:0 4px; user-select:none; }
.pf-arrow-fb { color:var(--c5); }

/* ── Phase 블록 ── */
.phases-wrapper { max-width:1100px; margin:0 auto; padding:0 16px 40px; display:flex; flex-direction:column; gap:16px; }
.phase-block { border-radius:12px; overflow:hidden; border:1.5px solid var(--border); background:#fff; }
.phase-header {
  display:flex; align-items:center; gap:12px; padding:14px 20px;
  cursor:pointer; user-select:none;
}
.phase-header:hover { filter:brightness(.97); }
.phase-num { font-size:12px; font-weight:700; letter-spacing:.5px; padding:3px 10px; border-radius:20px; background:rgba(0,0,0,.08); }
.phase-label { flex:1; font-size:15px; font-weight:600; }
.phase-toggle-icon { font-size:13px; color:var(--gray); transition:transform .25s; }
.phase-body { padding:12px 16px 16px; display:flex; flex-direction:column; gap:10px; }

/* Phase 색상 */
.phase-color-1 .phase-header { background:var(--c1l); } .phase-color-1 .phase-num { color:var(--c1); }
.phase-color-2 .phase-header { background:var(--c2l); } .phase-color-2 .phase-num { color:var(--c2); }
.phase-color-3 .phase-header { background:var(--c3l); } .phase-color-3 .phase-num { color:#b06000; }
.phase-color-4 .phase-header { background:var(--c4l); } .phase-color-4 .phase-num { color:var(--c4); }
.phase-color-5 .phase-header { background:var(--c5l); } .phase-color-5 .phase-num { color:var(--c5); }
.phase-color-6 .phase-header { background:var(--c6l); } .phase-color-6 .phase-num { color:var(--c6); }

/* ── 프로세스 카드 ── */
.process-card { border:1px solid var(--border); border-radius:8px; overflow:visible; }
.process-title {
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 14px; background:var(--light); cursor:pointer;
}
.process-title:hover { background:#ececec; }
.process-name { font-size:14px; font-weight:600; }
.toggle-icon { font-size:12px; color:var(--gray); transition:transform .25s; }
.process-body { padding:12px 14px; background:#fff; display:block; }

/* ── Split Card (좌우 2컨럼) ── */
.split-card { display:flex; gap:0; position:relative; min-height:40px; }
.split-left  { flex:1; min-width:0; padding:8px 12px 8px 6px; }
.split-right { flex:1; min-width:0; padding:8px 6px 8px 12px; border-left:1px dashed var(--border); }
.conn-svg { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; overflow:visible; z-index:1; }

/* ── BP 수직 플로우 ── */
.bp-flow-v { display:flex; flex-direction:column; gap:0; }
.bp-vbox {
  background:#fff; border:1.5px solid var(--border); border-radius:8px;
  padding:9px 12px; position:relative; cursor:default;
  transition:border-color .15s, box-shadow .15s, background .15s; z-index:2;
}
.bp-vbox:hover { border-color:var(--c1); box-shadow:0 2px 8px rgba(26,115,232,.18); }
.bp-vbox.bp-hi { border-color:var(--c1); background:#e8f0fe; }
.bp-vbox.bp-jump-hi {
  border-color:#e65100; background:#fff3e0;
  box-shadow:0 0 0 3px rgba(230,81,0,.35);
  animation: bp-pulse 0.5s ease 0s 3 alternate;
}
@keyframes bp-pulse {
  from { box-shadow:0 0 0 2px rgba(230,81,0,.3); }
  to   { box-shadow:0 0 0 6px rgba(230,81,0,.0); }
}
.bp-down-arrow { text-align:center; font-size:13px; color:#c0c0c0; padding:2px 0; line-height:1; user-select:none; }
.bp-id   { display:block; font-size:10px; font-weight:700; color:var(--c1); margin-bottom:3px; }
.bp-desc { display:block; font-size:12px; color:#3c4043; line-height:1.45; }
.bp-note-icon { position:absolute; top:5px; right:6px; font-size:11px; cursor:help; color:#9e9e9e; }

/* ── 서브그룹 레이블 / 크로스-그룹 화살표 ── */
.bp-subgroup-label {
  font-size:10px; font-weight:700; color:#1557b0;
  letter-spacing:.5px; text-transform:uppercase;
  padding:4px 8px; margin:6px 0 2px;
  background:#e8f0fe; border-radius:6px; text-align:center;
}
.bp-cross-arrow {
  text-align:center; font-size:13px; padding:3px 0; line-height:1;
  color:#1a73e8; user-select:none; font-weight:700;
}

/* ── WP 오른쪽 패널 ── */
.split-right-header {
  font-size:10px; font-weight:700; color:var(--gray);
  text-transform:uppercase; letter-spacing:.6px;
  margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid var(--border);
}
.wp-item {
  display:flex; align-items:center; gap:6px;
  padding:7px 10px; border:1.5px solid var(--border); border-radius:8px;
  cursor:pointer; margin-bottom:4px; background:#fff;
  position:relative; z-index:2;
  transition:border-color .15s, background .15s;
}
.wp-item:hover { border-color:var(--c1); background:#e8f0fe; }
.wp-item.wp-hi  { border-color:var(--c1); background:#e8f0fe; }
.wi-id   { font-size:11px; font-weight:700; color:var(--c1); white-space:nowrap; flex-shrink:0; }
.wi-name { font-size:11px; color:#3c4043; flex:1; line-height:1.3; }
.wi-arrow { font-size:9px; color:var(--gray); flex-shrink:0; }
.wi-link { font-size:13px; color:var(--c1); flex-shrink:0; font-weight:700; line-height:1; }
.wp-item:hover .wi-link { color:#e65100; }
.wp-item-detail {
  display:none; background:#f8f9fa; border:1px solid var(--border);
  border-radius:0 0 8px 8px; border-top:none;
  padding:8px 12px; margin-top:-4px; margin-bottom:4px; font-size:11px;
}
.wp-item-detail ul { padding-left:16px; }
.wp-item-detail li { margin-bottom:3px; line-height:1.5; color:#3c4043; }
.no-wp { color:var(--gray); font-size:12px; padding:6px; }

/* ── 유틸 ── */
.no-process { color:var(--gray); font-size:13px; padding:8px; }
.collapsed { display:none !important; }

/* ── Tab Bar ── */
.tab-bar {
  display:flex; gap:0; max-width:1100px; margin:0 auto 0;
  padding:0 16px; border-bottom:2px solid var(--border);
  background:#f1f3f4; position:sticky; top:0; z-index:100;
}
.tab-btn {
  padding:12px 28px; font-size:14px; font-weight:600;
  border:none; border-radius:8px 8px 0 0; cursor:pointer;
  background:transparent; color:var(--gray);
  transition:background .15s, color .15s;
  margin-bottom:-2px; border-bottom:2px solid transparent;
}
.tab-btn:hover { background:#e8eaed; color:#202124; }
.tab-btn.active { background:#fff; color:var(--c1); border-bottom:2px solid var(--c1); }
.tab-panel { display:none; }
.tab-panel.active { display:block; }

/* ── WP Flow 탭 ── */
.wf-wrapper { max-width:1100px; margin:0 auto; padding:16px 16px 40px; display:flex; flex-direction:column; gap:12px; }
.wf-category { border:1.5px solid var(--border); border-radius:12px; overflow:hidden; background:#fff; }
.wf-cat-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 20px; background:var(--light); cursor:pointer; user-select:none;
}
.wf-cat-header:hover { filter:brightness(.97); }
.wf-cat-title { font-size:14px; font-weight:700; color:#202124; }
.wf-cat-toggle { font-size:12px; color:var(--gray); transition:transform .25s; }
.wf-cat-body { padding:8px 16px 12px; display:flex; flex-direction:column; gap:4px; }
.wf-row { display:flex; align-items:flex-start; gap:8px; padding:3px 0; }
.wf-wp-side { flex:0 0 300px; min-width:0; }
.wf-conn { flex:0 0 24px; text-align:center; color:#c0c0c0; font-size:18px; padding-top:7px; user-select:none; }
.wf-bp-side { flex:1; display:flex; flex-wrap:wrap; align-content:flex-start; gap:4px; padding-top:5px; }
.wf-wp-card {
  display:flex; align-items:center; gap:6px; padding:7px 10px;
  border:1.5px solid var(--border); border-radius:8px; cursor:pointer;
  background:#fff; transition:border-color .15s, background .15s;
}
.wf-wp-card:hover { border-color:var(--c1); background:#e8f0fe; }
.wf-wp-id   { font-size:11px; font-weight:700; color:var(--c1); white-space:nowrap; flex-shrink:0; }
.wf-wp-name { font-size:11px; color:#3c4043; flex:1; line-height:1.3; }
.wf-wp-arr  { font-size:9px; color:var(--gray); flex-shrink:0; }
.wf-wp-detail {
  display:none; background:#f8f9fa; border:1px solid var(--border);
  border-radius:0 0 8px 8px; border-top:none;
  padding:8px 12px; font-size:11px; margin-top:-2px; margin-bottom:2px;
}
.wf-wp-detail ul { padding-left:16px; }
.wf-wp-detail li { color:#3c4043; line-height:1.5; margin-bottom:2px; }
.wf-bp-chip { font-size:10px; font-weight:600; padding:3px 9px; border-radius:12px; white-space:nowrap; cursor:pointer; transition:opacity .15s, box-shadow .15s; }
.wf-bp-chip:hover { opacity:.8; box-shadow:0 2px 6px rgba(0,0,0,.18); }
.wf-wp-card.wf-wp-jump-hi {
  border-color:#e65100; background:#fff3e0;
  box-shadow:0 0 0 3px rgba(230,81,0,.35);
  animation: bp-pulse 0.5s ease 0s 3 alternate;
}
"""

JS = """
const CONN_COLORS = ['#1a73e8','#0f9d58','#e65100','#7b1fa2','#c62828','#00838f','#558b2f','#f57c00'];

function drawAllConnections() {
  document.querySelectorAll('.split-card').forEach(card => {
    // 비활성 탭 내부이면 스킵
    const panel = card.closest('.tab-panel');
    if (panel && !panel.classList.contains('active')) return;
    let el = card;
    while (el) {
      if (el.classList && el.classList.contains('collapsed')) return;
      if (el.style && el.style.display === 'none') return;
      el = el.parentElement;
    }
    const svg = card.querySelector('.conn-svg');
    if (svg) drawCardConnections(card, svg);
  });
}

function drawCardConnections(card, svg) {
  svg.innerHTML = '';
  let conns;
  try { conns = JSON.parse(card.dataset.conns || '[]'); } catch(e) { return; }
  const r = card.getBoundingClientRect();
  svg.setAttribute('width', r.width);
  svg.setAttribute('height', r.height);
  conns.forEach(([bpId, wpIds], idx) => {
    const bpEl = document.getElementById(bpId);
    if (!bpEl) return;
    const color = CONN_COLORS[idx % CONN_COLORS.length];
    const br = bpEl.getBoundingClientRect();
    const x1 = br.right - r.left;
    const y1 = br.top + br.height / 2 - r.top;
    wpIds.forEach(wpId => {
      const wpEl = document.getElementById(wpId);
      if (!wpEl) return;
      const wr = wpEl.getBoundingClientRect();
      const x2 = wr.left - r.left;
      const y2 = wr.top + wr.height / 2 - r.top;
      const dx = Math.abs(x2 - x1) * 0.55;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${x1},${y1} C${x1+dx},${y1} ${x2-dx},${y2} ${x2},${y2}`);
      path.setAttribute('stroke', color); path.setAttribute('stroke-width', '1.8');
      path.setAttribute('fill', 'none'); path.setAttribute('opacity', '0.55');
      path.setAttribute('data-bp', bpId); path.setAttribute('data-wp', wpId);
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('cx', x2); dot.setAttribute('cy', y2); dot.setAttribute('r', '3');
      dot.setAttribute('fill', color); dot.setAttribute('opacity', '0.7');
      dot.setAttribute('data-bp', bpId); dot.setAttribute('data-wp', wpId);
      svg.appendChild(path); svg.appendChild(dot);
    });
  });
}

document.addEventListener('mouseover', e => {
  const tgt = e.target.closest('.bp-vbox') || e.target.closest('.wp-item');
  if (!tgt) return;
  const card = tgt.closest('.split-card');
  if (!card) return;
  const svg = card.querySelector('.conn-svg');
  if (!svg) return;
  const id = tgt.id;
  const isBp = tgt.classList.contains('bp-vbox');
  svg.querySelectorAll('path,circle').forEach(el => {
    const m = isBp ? el.dataset.bp === id : el.dataset.wp === id;
    el.setAttribute('opacity', m ? '1' : '0.06');
    if (el.tagName === 'path') el.setAttribute('stroke-width', m ? '2.5' : '1');
  });
  card.querySelectorAll('.bp-vbox').forEach(b => b.classList.toggle('bp-hi', b.id === id && isBp));
  card.querySelectorAll('.wp-item').forEach(w => w.classList.toggle('wp-hi', w.id === id && !isBp));
});

document.addEventListener('mouseout', e => {
  const tgt = e.target.closest('.bp-vbox') || e.target.closest('.wp-item');
  if (!tgt) return;
  const card = tgt.closest('.split-card');
  if (!card) return;
  const svg = card.querySelector('.conn-svg');
  if (svg) {
    svg.querySelectorAll('path').forEach(p => { p.setAttribute('opacity','0.55'); p.setAttribute('stroke-width','1.8'); });
    svg.querySelectorAll('circle').forEach(c => c.setAttribute('opacity','0.7'));
  }
  card.querySelectorAll('.bp-vbox').forEach(b => b.classList.remove('bp-hi'));
  card.querySelectorAll('.wp-item').forEach(w => w.classList.remove('wp-hi'));
});

function toggleWfDetail(detailId) {
  const detail = document.getElementById(detailId);
  if (!detail) return;
  const card = detail.previousElementSibling;
  const arrow = card ? card.querySelector('.wf-wp-arr') : null;
  if (detail.style.display === 'block') {
    detail.style.display = 'none';
    if (arrow) arrow.innerHTML = '&#9660;';
  } else {
    detail.style.display = 'block';
    if (arrow) arrow.innerHTML = '&#9650;';
  }
}

function toggleWfCat(catUid) {
  const body = document.getElementById(catUid);
  if (!body) return;
  const icon = body.closest('.wf-category').querySelector('.wf-cat-toggle');
  body.classList.toggle('collapsed');
  if (icon) icon.style.transform = body.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
}

function jumpToWp(wpUid) {
  const curTab = _activeTab();
  history.replaceState({ tab: curTab, scrollY: window.scrollY }, '');
  history.pushState({ tab: 'wp-flow', scrollY: 0 }, '');
  _historyJump = true;
  _applyTab('wp-flow', 0);
  _historyJump = false;

  const detailId = 'wfd_' + wpUid;
  const detailEl = document.getElementById(detailId);
  if (!detailEl) return;

  // 카테고리 접혀 있으면 펼치기
  const catBody = detailEl.closest('.wf-cat-body');
  if (catBody && catBody.classList.contains('collapsed')) {
    toggleWfCat(catBody.id);
  }
  // WP 상세 펼치기
  if (detailEl.style.display !== 'block') {
    toggleWfDetail(detailId);
  }
  // 스크롤 + 하이라이트
  setTimeout(() => {
    const card = detailEl.previousElementSibling;
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card.classList.add('wf-wp-jump-hi');
      setTimeout(() => card.classList.remove('wf-wp-jump-hi'), 2000);
    }
  }, 220);
}

function togglePhase(id) {
  const body = document.getElementById(id);
  const icon = body.closest('.phase-block').querySelector('.phase-toggle-icon');
  body.classList.toggle('collapsed');
  icon.style.transform = body.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
  if (!body.classList.contains('collapsed')) requestAnimationFrame(drawAllConnections);
}

function toggleCard(uid) {
  const body = document.getElementById('body-' + uid);
  const icon = document.getElementById('proc-' + uid).querySelector('.toggle-icon');
  body.classList.toggle('collapsed');
  icon.style.transform = body.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
  if (!body.classList.contains('collapsed')) requestAnimationFrame(drawAllConnections);
}

function scrollToPhase(short) {
  const el = document.getElementById('phase' + short);
  if (el) {
    el.classList.remove('collapsed');
    const icon = el.closest('.phase-block').querySelector('.phase-toggle-icon');
    icon.style.transform = '';
    el.closest('.phase-block').scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(drawAllConnections, 400);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  ['1','2','3','4','5','6'].forEach(n => {
    const body = document.getElementById('phase' + n);
    if (!body) return;
    if (n !== '3') {
      body.classList.add('collapsed');
      const icon = body.closest('.phase-block').querySelector('.phase-toggle-icon');
      icon.style.transform = 'rotate(-90deg)';
    }
  });
  requestAnimationFrame(drawAllConnections);
  // 초기 history state 등록
  history.replaceState({ tab: 'workflow', scrollY: 0 }, '');
});

// ── History (뒤로가기) 지원 ──
let _historyJump = false;  // popstate 중 재귀 방지

function _applyTab(name, scrollY) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.querySelector('.tab-btn[data-tab="' + name + '"]').classList.add('active');
  if (name === 'workflow') requestAnimationFrame(drawAllConnections);
  if (scrollY !== undefined) window.scrollTo({ top: scrollY, behavior: 'instant' });
}

window.addEventListener('popstate', e => {
  if (!e.state) return;
  _historyJump = true;
  _applyTab(e.state.tab, e.state.scrollY);
  _historyJump = false;
});

function switchTab(name) {
  if (!_historyJump) {
    // 현재 상태 저장 후 새 상태 push
    const cur = _activeTab();
    history.replaceState({ tab: cur, scrollY: window.scrollY }, '');
    history.pushState({ tab: name, scrollY: 0 }, '');
  }
  _applyTab(name, 0);
}

function _activeTab() {
  const p = document.querySelector('.tab-panel.active');
  return p ? p.id.replace('tab-', '') : 'workflow';
}

function jumpToBp(bpId) {
  // 현재 위치(WP Flow 탭 + 스크롤) 저장
  const curTab = _activeTab();
  history.replaceState({ tab: curTab, scrollY: window.scrollY }, '');
  history.pushState({ tab: 'workflow', scrollY: 0 }, '');

  // Workflow 탭 전환 (history push 없이)
  _historyJump = true;
  _applyTab('workflow', 0);
  _historyJump = false;

  // 대상 요소 탐색
  const bpEl = document.querySelector('[data-bp-id="' + bpId + '"]');
  if (!bpEl) return;

  // 상위 phase-body / process-body 모두 펼치기
  let el = bpEl.parentElement;
  while (el) {
    if (el.classList.contains('phase-body') && el.classList.contains('collapsed')) {
      togglePhase(el.id);
    }
    if (el.classList.contains('process-body') && el.classList.contains('collapsed')) {
      toggleCard(el.id.replace('body-', ''));
    }
    el = el.parentElement;
  }

  // 스크롤 + 하이라이트
  setTimeout(() => {
    bpEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    bpEl.classList.add('bp-jump-hi');
    setTimeout(() => bpEl.classList.remove('bp-jump-hi'), 1800);
    requestAnimationFrame(drawAllConnections);
  }, 320);
}
"""


def build_html(phases, phase_bp_map, bp_detail_map, wp_details) -> str:
    flow_html = render_phase_flow(phases)
    phase_blocks = ""
    for ph in phases:
        short = ph["id"].replace("Phase.", "")
        phase_blocks += render_phase_block(
            f"Phase.{short}", ph["label"], phase_bp_map, bp_detail_map, wp_details
        )

    wp_flow_html = render_wp_flow_tab(bp_detail_map, wp_details)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ASPICE v3.1 전체 중 S/W 프로젝트 관리 워크플로우</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>
<h1 class="page-title">ASPICE v3.1 — 전체 중 S/W 프로젝트 관리 워크플로우</h1>
<p class="subtitle">Workflow: Phase/BP 순서 탐색 &nbsp;|&nbsp; WP Flow: 산출물 기준 BP 연결 확인</p>

<div class="tab-bar">
  <button class="tab-btn active" data-tab="workflow" onclick="switchTab('workflow')">&#9881; Workflow</button>
  <button class="tab-btn" data-tab="wp-flow" onclick="switchTab('wp-flow')">&#128196; WP Flow</button>
</div>

<div id="tab-workflow" class="tab-panel active">
{flow_html}
<div class="phases-wrapper">
{phase_blocks}
</div>
</div>

<div id="tab-wp-flow" class="tab-panel">
{wp_flow_html}
</div>

<script>
{JS}
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
# 6. main
# ══════════════════════════════════════════════════════════════════════════════


def main():
    print("▶ WP 상세 파싱 중...")
    wp_details = parse_wp_details(WP_MD)
    print(f"  → {len(wp_details)}개 WP 로드")

    print("▶ 워크플로우 파싱 중...")
    phases, phase_bp_map, bp_detail_map = parse_workflow(WORKFLOW_MD)
    print(f"  → Phase {len(phases)}개, BP {len(bp_detail_map)}개")

    print("▶ HTML 생성 중...")
    html = build_html(phases, phase_bp_map, bp_detail_map, wp_details)

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✅ 완료: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
