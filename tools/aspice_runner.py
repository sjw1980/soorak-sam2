#!/usr/bin/env python3
"""
ASPICE 프로세스 순차 실행기 (Clipboard 기반)

워크플로우에 정의된 Phase/BP 순서대로 Agent 프롬프트를 클립보드에 복사하고,
사용자가 AI 답변을 붙여넣으면 산출물을 저장한 뒤 git commit까지 안내합니다.

사용법:
    python tools/aspice_runner.py              # 처음부터 시작
    python tools/aspice_runner.py --resume     # 마지막 완료 단계 이후부터 재개
    python tools/aspice_runner.py --status     # 현재 진행 상황 확인
    python tools/aspice_runner.py --step 12    # 특정 단계부터 시작
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── 프로젝트 루트 ──
PROJ_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = PROJ_ROOT / ".aspice-progress.json"
DOCS_DIR = PROJ_ROOT / "docs"

# ── 클립보드 유틸 ──

def copy_to_clipboard(text: str) -> bool:
    """텍스트를 시스템 클립보드에 복사합니다."""
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, shell=True
            )
            process.communicate(text.encode("utf-16le"))
        elif sys.platform == "darwin":
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE
            )
            process.communicate(text.encode("utf-8"))
        else:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
            )
            process.communicate(text.encode("utf-8"))
        return True
    except Exception as e:
        print(f"  [!] 클립보드 복사 실패: {e}")
        print(f"  [!] 아래 프롬프트를 수동으로 복사하세요.")
        return False


# ── Git 유틸 ──

def git_has_changes() -> bool:
    """워킹 디렉토리에 uncommitted 변경사항이 있는지 확인합니다."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, encoding="utf-8", cwd=PROJ_ROOT
    )
    # .aspice-progress.json 변경은 무시
    lines = [
        l for l in result.stdout.strip().splitlines()
        if not l.strip().endswith(".aspice-progress.json")
    ]
    return len(lines) > 0


def git_status_summary() -> str:
    """git status 요약을 반환합니다."""
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, encoding="utf-8", cwd=PROJ_ROOT
    )
    return result.stdout.strip()


def git_commit(message: str) -> bool:
    """모든 변경사항을 stage하고 commit합니다."""
    subprocess.run(["git", "add", "-A"], cwd=PROJ_ROOT, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True, text=True, encoding="utf-8", cwd=PROJ_ROOT
    )
    if result.returncode == 0:
        print(f"  [✓] 커밋 완료: {message}")
        return True
    else:
        print(f"  [!] 커밋 실패: {result.stderr.strip()}")
        return False


def create_step_directories(step: dict):
    """단계의 예상 산출물 디렉토리를 미리 생성합니다."""
    for expected in step["expected_outputs"]:
        path = PROJ_ROOT / expected
        # 확장자가 없으면 디렉터리로 간주
        if not path.suffix:
            path.mkdir(parents=True, exist_ok=True)


def verify_clean_state(step_name: str) -> bool:
    """다음 단계 진행 전 git 상태가 깨끗한지 확인합니다."""
    if git_has_changes():
        print(f"\n  ⚠️  커밋되지 않은 변경사항이 있습니다!")
        print(f"  현재 git status:")
        print(f"  {git_status_summary()}")
        print(f"\n  다음 단계({step_name})를 진행하려면 먼저 커밋하세요.")
        return False
    return True


# ── 진행 상태 관리 ──

def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_steps": [], "last_step_index": -1, "started_at": None}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════
#  ASPICE 워크플로우 단계 정의
# ══════════════════════════════════════════════════════════════════

STEPS = [
    # ── Phase 0: 킥오프 ──
    {
        "id": "PHASE0-KICKOFF",
        "phase": "Phase 0",
        "title": "프로젝트 킥오프 문서 작성",
        "agent": "(사람이 직접 작성)",
        "description": "AI Agent 실행 전, 사람이 docs/PROJECT-KICKOFF.md를 작성합니다.",
        "prompt": None,  # 클립보드 복사 없이 사람이 직접 작성
        "expected_outputs": ["docs/PROJECT-KICKOFF.md"],
        "commit_msg": "docs(man3): 프로젝트 킥오프 문서 작성",
    },

    # ── Phase 1.1: MAN.3 계획 ──
    {
        "id": "MAN3-BP1",
        "phase": "Phase 1.1",
        "title": "MAN.3.BP1 프로젝트 범위 정의",
        "agent": "ASPICE MAN-3 BP1 전문가",
        "description": "프로젝트 목표·동기·경계 식별, 프로젝트 계획서(WP.08-12) 초안 작성",
        "prompt": "@ASPICE MAN-3 BP1 전문가 docs/PROJECT-KICKOFF.md 를 읽고 프로젝트 범위 정의서를 작성해줘. 프로젝트 계획서(MAN3-PP-0001) 초안을 docs/MAN-3/ 에 생성해줘.",
        "expected_outputs": ["docs/MAN-3/"],
        "commit_msg": "docs(man3): BP1 프로젝트 범위 정의 — MAN3-PP-0001 초안",
    },
    {
        "id": "MAN3-BP2",
        "phase": "Phase 1.1",
        "title": "MAN.3.BP2 프로젝트 수명주기 정의",
        "agent": "ASPICE MAN-3 BP2 전문가",
        "prompt": "@ASPICE MAN-3 BP2 전문가 프로젝트 수명주기 모델을 정의하고 MAN3-PP-0001에 수명주기 섹션을 추가해줘.",
        "description": "프로젝트 수명주기 모델 선택·정의",
        "expected_outputs": ["docs/MAN-3/"],
        "commit_msg": "docs(man3): BP2 프로젝트 수명주기 정의",
    },
    {
        "id": "MAN3-BP3",
        "phase": "Phase 1.1",
        "title": "MAN.3.BP3 프로젝트 타당성 평가",
        "agent": "ASPICE MAN-3 BP3 전문가",
        "prompt": "@ASPICE MAN-3 BP3 전문가 프로젝트 타당성 평가를 수행하고 검토 기록(WP.13-19)을 docs/MAN-3/ 에 작성해줘.",
        "description": "시간·자원·기술 제약 내 목표 달성 가능성 평가",
        "expected_outputs": ["docs/MAN-3/"],
        "commit_msg": "docs(man3): BP3 프로젝트 타당성 평가",
    },

    # ── Phase 1.2: 지원 프로세스 전략 ──
    {
        "id": "SUP8-BP1",
        "phase": "Phase 1.2",
        "title": "SUP.8.BP1 형상관리 전략 수립",
        "agent": "ASPICE SUP-8 BP1 전문가",
        "prompt": "@ASPICE SUP-8 BP1 전문가 형상 관리 계획서(WP.08-04)와 복구 계획서(WP.08-14)를 docs/SUP-8/ 에 작성해줘. 프로젝트 계획서(MAN3-PP-0001)와 PROJECT-KICKOFF.md를 참조해.",
        "description": "형상 관리 전략 수립 — CMP, 복구 계획서",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP1 형상관리 전략 수립",
    },
    {
        "id": "SUP1-BP1",
        "phase": "Phase 1.2",
        "title": "SUP.1.BP1 품질보증 전략 수립",
        "agent": "ASPICE SUP-1 BP1 전문가",
        "prompt": "@ASPICE SUP-1 BP1 전문가 품질 계획서(WP.08-13)와 품질 기준(WP.18-07)을 docs/SUP-1/ 에 작성해줘. 기존 프로젝트 계획서를 참조해.",
        "description": "프로젝트 품질 보증 전략 개발",
        "expected_outputs": ["docs/SUP-1/"],
        "commit_msg": "docs(sup1): BP1 품질보증 전략 수립",
    },
    {
        "id": "SUP9-BP1",
        "phase": "Phase 1.2",
        "title": "SUP.9.BP1 문제해결 전략 수립",
        "agent": "ASPICE SUP-9 BP1 전문가",
        "prompt": "@ASPICE SUP-9 BP1 전문가 문제 관리 계획서(WP.08-27)를 docs/SUP-9/ 에 작성해줘. 문제 상태 모델, 경보 통지 전략, 긴급 해결 전략을 포함해.",
        "description": "문제 해결 관리 전략 수립",
        "expected_outputs": ["docs/SUP-9/"],
        "commit_msg": "docs(sup9): BP1 문제해결 전략 수립",
    },
    {
        "id": "SUP10-BP1",
        "phase": "Phase 1.2",
        "title": "SUP.10.BP1 변경요청 관리 전략 수립",
        "agent": "ASPICE SUP-10 BP1 전문가",
        "prompt": "@ASPICE SUP-10 BP1 전문가 변경 관리 계획서(WP.08-28)를 docs/SUP-10/ 에 작성해줘. CR 상태 모델, CCB 구성, 분석 기준을 포함해.",
        "description": "변경요청(CR) 관리 전략 수립",
        "expected_outputs": ["docs/SUP-10/"],
        "commit_msg": "docs(sup10): BP1 변경요청 관리 전략 수립",
    },

    # ── Phase 1.3: 테스트 전략 ──
    {
        "id": "SWE4-BP1",
        "phase": "Phase 1.3",
        "title": "SWE.4.BP1 SW 단위 검증 전략 수립",
        "agent": "ASPICE SWE-4 BP1 전문가",
        "prompt": "@ASPICE SWE-4 BP1 전문가 SW 단위 검증 전략 및 시험 계획서(WP.08-52)를 docs/SWE-4/ 에 작성해줘. 회귀 전략, 검증 방법, 커버리지 목표를 포함해.",
        "description": "SW 단위 검증 전략(회귀 전략 포함) 수립",
        "expected_outputs": ["docs/SWE-4/"],
        "commit_msg": "docs(swe4): BP1 단위 검증 전략 수립",
    },
    {
        "id": "SWE5-BP1",
        "phase": "Phase 1.3",
        "title": "SWE.5.BP1 SW 통합 전략 수립",
        "agent": "ASPICE SWE-5 BP1 전문가",
        "prompt": "@ASPICE SWE-5 BP1 전문가 SW 통합 전략 및 시험 계획서(WP.08-52)를 docs/SWE-5/ 에 작성해줘. SW 아이템 식별, 통합 순서를 포함해.",
        "description": "SW 통합 전략 수립",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "docs(swe5): BP1 통합 전략 수립",
    },
    {
        "id": "SWE5-BP2",
        "phase": "Phase 1.3",
        "title": "SWE.5.BP2 SW 통합 테스트 전략 수립",
        "agent": "ASPICE SWE-5 BP2 전문가",
        "prompt": "@ASPICE SWE-5 BP2 전문가 SW 통합 시험 전략(회귀 시험 전략 포함)을 docs/SWE-5/ 시험 계획서에 추가해줘.",
        "description": "SW 통합 시험 전략(회귀 포함) 수립",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "docs(swe5): BP2 통합 테스트 전략 수립",
    },
    {
        "id": "SWE6-BP1",
        "phase": "Phase 1.3",
        "title": "SWE.6.BP1 SW 적격성 테스트 전략 수립",
        "agent": "ASPICE SWE-6 BP1 전문가",
        "prompt": "@ASPICE SWE-6 BP1 전문가 SW 적격성 테스트 전략 및 시험 계획서(WP.08-52, WP.19-00)를 docs/SWE-6/ 에 작성해줘.",
        "description": "SW 인정 시험 전략(회귀 포함) 수립",
        "expected_outputs": ["docs/SWE-6/"],
        "commit_msg": "docs(swe6): BP1 적격성 테스트 전략 수립",
    },

    # ── Phase 1.4: WBS ──
    {
        "id": "MAN3-BP4",
        "phase": "Phase 1.4",
        "title": "MAN.3.BP4 프로젝트 활동 및 WBS 정의",
        "agent": "ASPICE MAN-3 BP4 전문가",
        "prompt": "@ASPICE MAN-3 BP4 전문가 프로젝트 활동과 WBS를 정의해줘. MAN3-PP-0001의 WBS 섹션과 일정(WP.14-06), WBS(WP.14-09)를 docs/MAN-3/ 에 작성해줘. 지금까지 작성된 모든 전략 문서를 참조해.",
        "description": "프로젝트 활동·WBS·일정 정의",
        "expected_outputs": ["docs/MAN-3/"],
        "commit_msg": "docs(man3): BP4 WBS 및 일정 정의",
    },

    # ── Phase 2: 환경 구축 ──
    {
        "id": "SUP8-BP2",
        "phase": "Phase 2",
        "title": "SUP.8.BP2 형상 항목 식별",
        "agent": "ASPICE SUP-8 BP2 전문가",
        "prompt": "@ASPICE SUP-8 BP2 전문가 형상 항목(CI) 목록을 식별하고 docs/SUP-8/ 에 형상 관리 기록(WP.13-10)을 작성해줘. 현재 프로젝트의 모든 산출물을 CI로 등록해.",
        "description": "형상 항목 식별 및 기록",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP2 형상 항목 식별",
    },
    {
        "id": "SUP8-BP3",
        "phase": "Phase 2",
        "title": "SUP.8.BP3 형상관리 시스템 구축",
        "agent": "ASPICE SUP-8 BP3 전문가",
        "prompt": "@ASPICE SUP-8 BP3 전문가 형상 관리 시스템 구축 기록을 docs/SUP-8/ 에 작성해줘. 저장소 구성, 접근 권한, 변경 이력 관리 방법을 문서화해.",
        "description": "형상 관리 시스템 수립",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP3 형상관리 시스템 구축",
    },
    {
        "id": "SUP1-BP2",
        "phase": "Phase 2",
        "title": "SUP.1.BP2 프로세스 준수성 보증 활동 시작",
        "agent": "ASPICE SUP-1 BP2 전문가",
        "prompt": "@ASPICE SUP-1 BP2 전문가 Phase 1 산출물에 대한 품질 보증 검토를 수행하고, 검토 기록(WP.13-19)과 품질 기록(WP.13-18)을 docs/SUP-1/ 에 작성해줘.",
        "description": "작업 산출물 품질 보증 검토",
        "expected_outputs": ["docs/SUP-1/"],
        "commit_msg": "docs(sup1): BP2 산출물 품질보증 검토",
    },

    # ── Phase 3: SWE.1 요구사항 분석 ──
    {
        "id": "SWE1-BP1",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP1 SW 요구사항 명세",
        "agent": "ASPICE SWE-1 BP1 전문가",
        "prompt": "@ASPICE SWE-1 BP1 전문가 PROJECT-KICKOFF.md와 프로젝트 계획서를 참조하여 SW 요구사항 명세서(WP.17-11)를 docs/SWE-1/ 에 작성해줘. 기능적·비기능적 요구사항을 식별하고 ID를 부여해.",
        "description": "SW 기능적·비기능적 요구사항 명세",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP1 SW 요구사항 명세",
    },
    {
        "id": "SWE1-BP2",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP2 SW 요구사항 구조화",
        "agent": "ASPICE SWE-1 BP2 전문가",
        "prompt": "@ASPICE SWE-1 BP2 전문가 작성된 SW 요구사항을 그룹화·우선순위화·카테고리화해줘. 검증 기준 입력도 제공해.",
        "description": "요구사항 그룹화·우선순위화·카테고리화",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP2 요구사항 구조화",
    },
    {
        "id": "SWE1-BP3",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP3 SW 요구사항 분석",
        "agent": "ASPICE SWE-1 BP3 전문가",
        "prompt": "@ASPICE SWE-1 BP3 전문가 요구사항의 정확성·기술적 실현가능성·검증가능성을 분석하고, 비용/일정/기술적 영향을 분석해줘.",
        "description": "요구사항 정확성·실현가능성·검증가능성 분석",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP3 요구사항 분석",
    },
    {
        "id": "SWE1-BP4",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP4 운영 환경 영향 분석",
        "agent": "ASPICE SWE-1 BP4 전문가",
        "prompt": "@ASPICE SWE-1 BP4 전문가 SW 요구사항이 HW/OS 등 운영 환경에 미치는 영향을 분석해줘.",
        "description": "운영 환경 영향 분석",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP4 운영 환경 영향 분석",
    },
    {
        "id": "SWE1-BP5",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP5 검증 기준 개발",
        "agent": "ASPICE SWE-1 BP5 전문가",
        "prompt": "@ASPICE SWE-1 BP5 전문가 각 SW 요구사항에 대한 검증 기준(WP.17-50)을 개발해줘.",
        "description": "각 요구사항별 검증 기준 개발",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP5 검증 기준 개발",
    },
    {
        "id": "SWE1-BP6",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP6 양방향 추적성 수립",
        "agent": "ASPICE SWE-1 BP6 전문가",
        "prompt": "@ASPICE SWE-1 BP6 전문가 시스템 요구사항↔SW 요구사항 간 양방향 추적성 매핑표(WP.13-22)를 작성해줘.",
        "description": "시스템 요구사항↔SW 요구사항 양방향 추적성",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP6 양방향 추적성 수립",
    },
    {
        "id": "SWE1-BP7",
        "phase": "Phase 3 — SWE.1",
        "title": "SWE.1.BP7 일관성 확보",
        "agent": "ASPICE SWE-1 BP7 전문가",
        "prompt": "@ASPICE SWE-1 BP7 전문가 시스템 요구사항과 SW 요구사항 간 일관성을 검토하고 검토 기록(WP.13-19)을 작성해줘.",
        "description": "요구사항 일관성 검토",
        "expected_outputs": ["docs/SWE-1/"],
        "commit_msg": "docs(swe1): BP7 일관성 확보",
    },
    {
        "id": "SUP8-BP4-SWE1",
        "phase": "Phase 3 — SWE.1",
        "title": "SUP.8.BP4 요구사항 베이스라인 설정",
        "agent": "ASPICE SUP-8 BP4 전문가",
        "prompt": "@ASPICE SUP-8 BP4 전문가 SWE.1 완료에 따른 요구사항 베이스라인을 설정하고, 베이스라인 기록(WP.13-08)을 docs/SUP-8/ 에 작성해줘.",
        "description": "SWE.1 요구사항 베이스라인 설정",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP4 요구사항 베이스라인 설정",
    },

    # ── Phase 3: SWE.2 아키텍처 설계 ──
    {
        "id": "SWE2-BP1",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP1 SW 아키텍처 설계 개발",
        "agent": "ASPICE SWE-2 BP1 전문가",
        "prompt": "@ASPICE SWE-2 BP1 전문가 SW 요구사항 명세서를 참조하여 SW 아키텍처 설계서(WP.04-04)를 docs/SWE-2/ 에 작성해줘. 컴포넌트 분해 구조를 정의해.",
        "description": "SW 아키텍처 설계 개발",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP1 아키텍처 설계 개발",
    },
    {
        "id": "SWE2-BP2",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP2 아키텍처에 요구사항 할당",
        "agent": "ASPICE SWE-2 BP2 전문가",
        "prompt": "@ASPICE SWE-2 BP2 전문가 SW 요구사항을 아키텍처 컴포넌트에 할당하고 매핑표를 아키텍처 설계서에 추가해줘.",
        "description": "SW 요구사항을 아키텍처 앨리먼트에 할당",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP2 요구사항 할당",
    },
    {
        "id": "SWE2-BP3",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP3 인터페이스 정의",
        "agent": "ASPICE SWE-2 BP3 전문가",
        "prompt": "@ASPICE SWE-2 BP3 전문가 각 SW 앨리먼트의 인터페이스를 정의하고 인터페이스 요구사항 명세서(WP.17-08)를 작성해줘.",
        "description": "SW 앨리먼트 인터페이스 정의",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP3 인터페이스 정의",
    },
    {
        "id": "SWE2-BP4",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP4 동적 동작 설명",
        "agent": "ASPICE SWE-2 BP4 전문가",
        "prompt": "@ASPICE SWE-2 BP4 전문가 SW 앨리먼트의 동적 행태(운영 모드, 타이밍, 상호작용)를 아키텍처 설계서에 추가해줘.",
        "description": "동적 행태 서술",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP4 동적 동작 설명",
    },
    {
        "id": "SWE2-BP5",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP5 SW 아키텍처 평가",
        "agent": "ASPICE SWE-2 BP5 전문가",
        "prompt": "@ASPICE SWE-2 BP5 전문가 자원 소모 목표를 정의하고 아키텍처 설계서에 추가해줘.",
        "description": "자원 소모 목표 정의",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP5 자원 소모 목표 정의",
    },
    {
        "id": "SWE2-BP6",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP6 대안 아키텍처 평가",
        "agent": "ASPICE SWE-2 BP6 전문가",
        "prompt": "@ASPICE SWE-2 BP6 전문가 대안 아키텍처를 평가하고 선정 근거를 기록해줘.",
        "description": "대안 아키텍처 평가 및 선정 근거 기록",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP6 대안 아키텍처 평가",
    },
    {
        "id": "SWE2-BP7",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP7 양방향 추적성 수립",
        "agent": "ASPICE SWE-2 BP7 전문가",
        "prompt": "@ASPICE SWE-2 BP7 전문가 SW 요구사항↔아키텍처 앨리먼트 간 양방향 추적성(WP.13-22)을 수립해줘.",
        "description": "SW 요구사항↔아키텍처 양방향 추적성",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP7 양방향 추적성 수립",
    },
    {
        "id": "SWE2-BP8",
        "phase": "Phase 3 — SWE.2",
        "title": "SWE.2.BP8 일관성 확보",
        "agent": "ASPICE SWE-2 BP8 전문가",
        "prompt": "@ASPICE SWE-2 BP8 전문가 SW 요구사항과 아키텍처 설계 간 일관성을 검토하고 검토 기록(WP.13-19)을 작성해줘.",
        "description": "요구사항-아키텍처 일관성 검토",
        "expected_outputs": ["docs/SWE-2/"],
        "commit_msg": "docs(swe2): BP8 일관성 확보",
    },
    {
        "id": "SUP8-BP4-SWE2",
        "phase": "Phase 3 — SWE.2",
        "title": "SUP.8.BP4 아키텍처 베이스라인 설정",
        "agent": "ASPICE SUP-8 BP4 전문가",
        "prompt": "@ASPICE SUP-8 BP4 전문가 SWE.2 완료에 따른 아키텍처 베이스라인을 설정하고 기록해줘.",
        "description": "SWE.2 아키텍처 베이스라인 설정",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP4 아키텍처 베이스라인 설정",
    },

    # ── Phase 3: SWE.3 상세 설계 및 유닛 개발 ──
    {
        "id": "SWE3-BP1",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP1 SW 상세 설계 개발",
        "agent": "ASPICE SWE-3 BP1 전문가",
        "prompt": "@ASPICE SWE-3 BP1 전문가 아키텍처 설계서를 참조하여 SW 상세 설계서(WP.04-05)를 docs/SWE-3/ 에 작성해줘. 모든 SW 유닛을 명세해.",
        "description": "SW 상세 설계 개발",
        "expected_outputs": ["docs/SWE-3/"],
        "commit_msg": "docs(swe3): BP1 상세 설계 개발",
    },
    {
        "id": "SWE3-BP2",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP2 상세 인터페이스 정의",
        "agent": "ASPICE SWE-3 BP2 전문가",
        "prompt": "@ASPICE SWE-3 BP2 전문가 각 SW 유닛 간 인터페이스를 상세 설계서에 추가해줘.",
        "description": "SW 유닛 간 인터페이스 명세",
        "expected_outputs": ["docs/SWE-3/"],
        "commit_msg": "docs(swe3): BP2 상세 인터페이스 정의",
    },
    {
        "id": "SWE3-BP3",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP3 동적 동작 설명",
        "agent": "ASPICE SWE-3 BP3 전문가",
        "prompt": "@ASPICE SWE-3 BP3 전문가 SW 유닛의 동적 행태를 상세 설계서에 추가해줘.",
        "description": "SW 유닛 동적 행태 서술",
        "expected_outputs": ["docs/SWE-3/"],
        "commit_msg": "docs(swe3): BP3 동적 동작 설명",
    },
    {
        "id": "SWE3-BP4",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP4 상세 설계 평가",
        "agent": "ASPICE SWE-3 BP4 전문가",
        "prompt": "@ASPICE SWE-3 BP4 전문가 SW 상세 설계를 평가하고 검토 기록을 작성해줘.",
        "description": "상세 설계 평가",
        "expected_outputs": ["docs/SWE-3/"],
        "commit_msg": "docs(swe3): BP4 상세 설계 평가",
    },
    {
        "id": "SWE3-BP5",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP5 SW Unit 개발/코딩",
        "agent": "ASPICE SWE-3 BP8 전문가",
        "prompt": "@ASPICE SWE-3 BP8 전문가 상세 설계서에 따라 SW 유닛(소스코드)을 구현해줘. src/ 폴더에 코드를 작성해.",
        "description": "SW 유닛 소스코드 구현",
        "expected_outputs": ["src/"],
        "commit_msg": "feat(swe3): BP8 SW 유닛 구현",
    },
    {
        "id": "SWE3-BP6",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP6 양방향 추적성 수립",
        "agent": "ASPICE SWE-3 BP5 전문가",
        "prompt": "@ASPICE SWE-3 BP5 전문가 SW 요구사항↔SW 유닛, 아키텍처↔상세설계 간 양방향 추적성을 수립해줘.",
        "description": "요구사항-유닛 양방향 추적성",
        "expected_outputs": ["docs/SWE-3/"],
        "commit_msg": "docs(swe3): BP5 양방향 추적성 수립",
    },
    {
        "id": "SWE3-BP7",
        "phase": "Phase 3 — SWE.3",
        "title": "SWE.3.BP7 일관성 확보",
        "agent": "ASPICE SWE-3 BP6 전문가",
        "prompt": "@ASPICE SWE-3 BP6 전문가 요구사항-유닛 간, 아키텍처-상세설계-유닛 간 일관성을 검토하고 검토 기록을 작성해줘.",
        "description": "설계-코드 일관성 검토",
        "expected_outputs": ["docs/SWE-3/"],
        "commit_msg": "docs(swe3): BP6 일관성 확보",
    },

    # ── Phase 3: SWE.4 단위 검증 ──
    {
        "id": "SWE4-BP2",
        "phase": "Phase 3 — SWE.4",
        "title": "SWE.4.BP2 단위 검증 기준 개발",
        "agent": "ASPICE SWE-4 BP2 전문가",
        "prompt": "@ASPICE SWE-4 BP2 전문가 유닛 시험 명세서(WP.08-50)를 docs/SWE-4/ 에 작성해줘. 시험 케이스, 시험 데이터, 커버리지 목표를 포함해.",
        "description": "유닛 시험 케이스·기준 개발",
        "expected_outputs": ["docs/SWE-4/"],
        "commit_msg": "docs(swe4): BP2 단위 검증 기준 개발",
    },
    {
        "id": "SWE4-BP3",
        "phase": "Phase 3 — SWE.4",
        "title": "SWE.4.BP3 정적 단위 검증 수행",
        "agent": "ASPICE SWE-4 BP3 전문가",
        "prompt": "@ASPICE SWE-4 BP3 전문가 SW 유닛에 대한 정적 검증(코드 검토, 정적 분석)을 수행하고 결과를 기록해줘.",
        "description": "정적 분석·코드 검토 수행",
        "expected_outputs": ["docs/SWE-4/"],
        "commit_msg": "docs(swe4): BP3 정적 단위 검증 수행",
    },
    {
        "id": "SWE4-BP4",
        "phase": "Phase 3 — SWE.4",
        "title": "SWE.4.BP4 SW 단위 테스트 수행",
        "agent": "ASPICE SWE-4 BP4 전문가",
        "prompt": "@ASPICE SWE-4 BP4 전문가 유닛 시험 명세서에 따라 단위 테스트를 작성하고 실행해줘. tests/ 폴더에 테스트 코드를 작성하고 결과를 기록해.",
        "description": "단위 테스트 작성 및 실행",
        "expected_outputs": ["tests/", "docs/SWE-4/"],
        "commit_msg": "test(swe4): BP4 단위 테스트 수행",
    },
    {
        "id": "SWE4-BP5",
        "phase": "Phase 3 — SWE.4",
        "title": "SWE.4.BP5 양방향 추적성 수립",
        "agent": "ASPICE SWE-4 BP5 전문가",
        "prompt": "@ASPICE SWE-4 BP5 전문가 SW 유닛↔정적 검증 결과, 상세 설계↔시험 명세서, 시험 명세서↔시험 결과 간 양방향 추적성을 수립해줘.",
        "description": "유닛-TC-결과 양방향 추적성",
        "expected_outputs": ["docs/SWE-4/"],
        "commit_msg": "docs(swe4): BP5 양방향 추적성 수립",
    },
    {
        "id": "SWE4-BP6",
        "phase": "Phase 3 — SWE.4",
        "title": "SWE.4.BP6 일관성 확보",
        "agent": "ASPICE SWE-4 BP6 전문가",
        "prompt": "@ASPICE SWE-4 BP6 전문가 상세 설계와 유닛 시험 명세서 간 일관성을 검토하고 검토 기록을 작성해줘.",
        "description": "설계-테스트 일관성 검토",
        "expected_outputs": ["docs/SWE-4/"],
        "commit_msg": "docs(swe4): BP6 일관성 확보",
    },

    # ── Phase 3: SWE.5 통합 ──
    {
        "id": "SWE5-BP3",
        "phase": "Phase 3 — SWE.5",
        "title": "SWE.5.BP3 통합 테스트 케이스 개발",
        "agent": "ASPICE SWE-5 BP3 전문가",
        "prompt": "@ASPICE SWE-5 BP3 전문가 통합 시험 명세서(WP.08-50)를 docs/SWE-5/ 에 작성해줘. 각 통합 SW 아이템별 시험 케이스를 포함해.",
        "description": "통합 시험 명세서 개발",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "docs(swe5): BP3 통합 테스트 케이스 개발",
    },
    {
        "id": "SWE5-BP4",
        "phase": "Phase 3 — SWE.5",
        "title": "SWE.5.BP4 SW Unit 통합",
        "agent": "ASPICE SWE-5 BP4 전문가",
        "prompt": "@ASPICE SWE-5 BP4 전문가 SW 유닛을 SW 아이템으로 통합하고, 빌드 목록(WP.17-02)을 docs/SWE-5/ 에 작성해줘.",
        "description": "SW 유닛 통합 및 빌드",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "docs(swe5): BP4 SW 유닛 통합",
    },
    {
        "id": "SUP8-BP4-SWE5",
        "phase": "Phase 3 — SWE.5",
        "title": "SUP.8.BP4 통합 빌드 베이스라인 설정",
        "agent": "ASPICE SUP-8 BP4 전문가",
        "prompt": "@ASPICE SUP-8 BP4 전문가 SWE.5 통합 빌드에 대한 베이스라인을 설정하고 기록해줘.",
        "description": "통합 빌드 베이스라인 설정",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP4 통합 빌드 베이스라인",
    },
    {
        "id": "SWE5-BP5",
        "phase": "Phase 3 — SWE.5",
        "title": "SWE.5.BP5 통합 SW 테스트 수행",
        "agent": "ASPICE SWE-5 BP5 전문가",
        "prompt": "@ASPICE SWE-5 BP5 전문가 통합 시험 케이스를 선택하고, @ASPICE SWE-5 BP6 전문가 통합 테스트를 수행하고 결과를 기록해줘.",
        "description": "통합 테스트 선택·수행·결과 기록",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "test(swe5): BP5-BP6 통합 테스트 수행",
    },
    {
        "id": "SWE5-BP7",
        "phase": "Phase 3 — SWE.5",
        "title": "SWE.5.BP7 양방향 추적성 수립",
        "agent": "ASPICE SWE-5 BP7 전문가",
        "prompt": "@ASPICE SWE-5 BP7 전문가 아키텍처↔통합 시험 케이스, 시험 케이스↔결과 간 양방향 추적성을 수립해줘.",
        "description": "아키텍처-ITC-결과 양방향 추적성",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "docs(swe5): BP7 양방향 추적성 수립",
    },
    {
        "id": "SWE5-BP8",
        "phase": "Phase 3 — SWE.5",
        "title": "SWE.5.BP8 일관성 확보",
        "agent": "ASPICE SWE-5 BP8 전문가",
        "prompt": "@ASPICE SWE-5 BP8 전문가 아키텍처와 통합 시험 케이스 간 일관성을 검토하고 검토 기록을 작성해줘.",
        "description": "아키텍처-통합테스트 일관성 검토",
        "expected_outputs": ["docs/SWE-5/"],
        "commit_msg": "docs(swe5): BP8 일관성 확보",
    },

    # ── Phase 3: SWE.6 적격성 테스트 ──
    {
        "id": "SWE6-BP2",
        "phase": "Phase 3 — SWE.6",
        "title": "SWE.6.BP2 적격성 테스트 케이스 개발",
        "agent": "ASPICE SWE-6 BP2 전문가",
        "prompt": "@ASPICE SWE-6 BP2 전문가 적격성 시험 명세서(WP.08-50)를 docs/SWE-6/ 에 작성해줘. SW 요구사항 기반 시험 케이스를 포함해.",
        "description": "적격성 시험 명세서 개발",
        "expected_outputs": ["docs/SWE-6/"],
        "commit_msg": "docs(swe6): BP2 적격성 테스트 케이스 개발",
    },
    {
        "id": "SWE6-BP3",
        "phase": "Phase 3 — SWE.6",
        "title": "SWE.6.BP3 통합 SW 적격성 테스트 수행",
        "agent": "ASPICE SWE-6 BP3 전문가",
        "prompt": "@ASPICE SWE-6 BP3 전문가 적격성 시험 케이스를 선택하고 실행하고 결과(WP.13-50)를 기록해줘.",
        "description": "적격성 테스트 선택·수행·결과 기록",
        "expected_outputs": ["docs/SWE-6/"],
        "commit_msg": "test(swe6): BP3 적격성 테스트 수행",
    },
    {
        "id": "SWE6-BP4",
        "phase": "Phase 3 — SWE.6",
        "title": "SWE.6.BP4 양방향 추적성 수립",
        "agent": "ASPICE SWE-6 BP5 전문가",
        "prompt": "@ASPICE SWE-6 BP5 전문가 SW 요구사항↔적격성 시험 케이스, 시험 케이스↔결과 간 양방향 추적성을 수립해줘.",
        "description": "요구사항-QTC-결과 양방향 추적성",
        "expected_outputs": ["docs/SWE-6/"],
        "commit_msg": "docs(swe6): BP5 양방향 추적성 수립",
    },
    {
        "id": "SWE6-BP5",
        "phase": "Phase 3 — SWE.6",
        "title": "SWE.6.BP5 일관성 확보",
        "agent": "ASPICE SWE-6 BP6 전문가",
        "prompt": "@ASPICE SWE-6 BP6 전문가 SW 요구사항과 적격성 시험 명세서 간 일관성을 검토하고 검토 기록을 작성해줘.",
        "description": "요구사항-적격성테스트 일관성 검토",
        "expected_outputs": ["docs/SWE-6/"],
        "commit_msg": "docs(swe6): BP6 일관성 확보",
    },

    # ── Phase 4.1: 출시/배포 ──
    {
        "id": "SUP1-BP3",
        "phase": "Phase 4.1",
        "title": "SUP.1.BP3 최종 QA Audit",
        "agent": "ASPICE SUP-1 BP3 전문가",
        "prompt": "@ASPICE SUP-1 BP3 전문가 최종 프로덕트 준수성 보증(QA Audit)을 수행하고 검토 기록과 품질 기록을 docs/SUP-1/ 에 작성해줘.",
        "description": "최종 프로세스 활동 품질 보증",
        "expected_outputs": ["docs/SUP-1/"],
        "commit_msg": "docs(sup1): BP3 최종 QA Audit",
    },
    {
        "id": "SUP8-BP8",
        "phase": "Phase 4.1",
        "title": "SUP.8.BP8 형상관리 정보 검증",
        "agent": "ASPICE SUP-8 BP8 전문가",
        "prompt": "@ASPICE SUP-8 BP8 전문가 형상화된 항목과 베이스라인 정보의 완전성을 검증하고 감사 체크리스트를 작성해줘.",
        "description": "베이스라인 심사·형상 감사",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP8 형상관리 정보 검증",
    },
    {
        "id": "SUP8-BP5",
        "phase": "Phase 4.1",
        "title": "SUP.8.BP5 수정 및 릴리즈 통제",
        "agent": "ASPICE SUP-8 BP5 전문가",
        "prompt": "@ASPICE SUP-8 BP5 전문가 수정과 릴리즈 통제 체계를 수립하고 기록해줘.",
        "description": "수정·출시 통제 체계 수립",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP5 수정 및 릴리즈 통제",
    },
    {
        "id": "SUP8-BP9",
        "phase": "Phase 4.1",
        "title": "SUP.8.BP9 릴리즈 관리",
        "agent": "ASPICE SUP-8 BP9 전문가",
        "prompt": "@ASPICE SUP-8 BP9 전문가 형상 항목과 베이스라인의 저장 관리 기록을 작성해줘.",
        "description": "형상 항목 저장·보관·백업 관리",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP9 릴리즈 관리",
    },
    {
        "id": "SUP8-BP6",
        "phase": "Phase 4.1",
        "title": "SUP.8.BP6 형상 이력 유지",
        "agent": "ASPICE SUP-8 BP6 전문가",
        "prompt": "@ASPICE SUP-8 BP6 전문가 최종 베이스라인을 수립하고 베이스라인 기록을 갱신해줘.",
        "description": "최종 베이스라인 수립",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP6 형상 이력 유지",
    },
    {
        "id": "SUP8-BP7",
        "phase": "Phase 4.1",
        "title": "SUP.8.BP7 형상 상태 보고",
        "agent": "ASPICE SUP-8 BP7 전문가",
        "prompt": "@ASPICE SUP-8 BP7 전문가 형상 상태 보고서를 작성해줘. 모든 CI의 현재 상태를 포함해.",
        "description": "형상 상태 보고서 작성",
        "expected_outputs": ["docs/SUP-8/"],
        "commit_msg": "docs(sup8): BP7 형상 상태 보고",
    },

    # ── Phase 4.2: 출시 준비 및 빌드 ──
    {
        "id": "SPL2-BP1",
        "phase": "Phase 4.2",
        "title": "SPL.2.BP1 출시 기능 내용 정의",
        "agent": "ASPICE SPL-2 BP1 전문가",
        "prompt": "@ASPICE SPL-2 BP1 전문가 출시 계획서(WP.08-16)와 제품 출시 정보(WP.11-03)를 docs/SPL-2/ 에 작성해줘.",
        "description": "출시 기능 범위 식별·계획",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP1 출시 기능 내용 정의",
    },
    {
        "id": "SPL2-BP2",
        "phase": "Phase 4.2",
        "title": "SPL.2.BP2 출시 제품 정의",
        "agent": "ASPICE SPL-2 BP2 전문가",
        "prompt": "@ASPICE SPL-2 BP2 전문가 출시 제품 항목을 정의하고 출시 계획서를 갱신해줘.",
        "description": "출시 제품 항목 식별",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP2 출시 제품 정의",
    },
    {
        "id": "SPL2-BP3",
        "phase": "Phase 4.2",
        "title": "SPL.2.BP3 출시 분류/번호 체계 수립",
        "agent": "ASPICE SPL-2 BP3 전문가",
        "prompt": "@ASPICE SPL-2 BP3 전문가 제품 출시 분류와 번호 부여 체계를 수립해줘.",
        "description": "버전 넘버링·출시 분류 체계 수립",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP3 출시 분류/번호 체계",
    },
    {
        "id": "SPL2-BP4",
        "phase": "Phase 4.2",
        "title": "SPL.2.BP4 빌드 활동/환경 정의",
        "agent": "ASPICE SPL-2 BP4 전문가",
        "prompt": "@ASPICE SPL-2 BP4 전문가 빌드 활동과 빌드 환경을 정의하고 문서화해줘.",
        "description": "빌드 프로세스·환경 정의",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP4 빌드 활동/환경 정의",
    },
    {
        "id": "SPL2-BP5",
        "phase": "Phase 4.2",
        "title": "SPL.2.BP5 출시 빌드",
        "agent": "ASPICE SPL-2 BP5 전문가",
        "prompt": "@ASPICE SPL-2 BP5 전문가 형상 항목으로부터 출시 빌드를 수행하고 결과를 기록해줘.",
        "description": "형상 항목 기반 출시 빌드 수행",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP5 출시 빌드 수행",
    },

    # ── Phase 4.3: 배포 및 종료 ──
    {
        "id": "SPL2-BP7",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP7 전달 매체 유형 결정",
        "agent": "ASPICE SPL-2 BP7 전문가",
        "prompt": "@ASPICE SPL-2 BP7 전문가 제품 전달을 위한 매체 유형을 결정하고 문서화해줘.",
        "description": "전달 매체 유형 결정",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP7 전달 매체 유형 결정",
    },
    {
        "id": "SPL2-BP8",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP8 출시 매체 패키징",
        "agent": "ASPICE SPL-2 BP8 전문가",
        "prompt": "@ASPICE SPL-2 BP8 전문가 출시 매체 패키징을 식별하고 문서화해줘.",
        "description": "전달 매체 패키징 정의",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP8 출시 매체 패키징",
    },
    {
        "id": "SPL2-BP9",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP9 출시 노트 작성",
        "agent": "ASPICE SPL-2 BP9 전문가",
        "prompt": "@ASPICE SPL-2 BP9 전문가 출시 노트를 작성하고 출시 문서를 최종화해줘.",
        "description": "출시 노트·문서 작성",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP9 출시 노트 작성",
    },
    {
        "id": "SPL2-BP10",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP10 제품 출시 승인",
        "agent": "ASPICE SPL-2 BP10 전문가",
        "prompt": "@ASPICE SPL-2 BP10 전문가 출시 기준 충족 여부를 확인하고 출시 승인 기록(WP.13-13)을 작성해줘.",
        "description": "출시 기준 검증·승인 획득",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP10 제품 출시 승인",
    },
    {
        "id": "SPL2-BP11",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP11 출시 일관성 보장",
        "agent": "ASPICE SPL-2 BP11 전문가",
        "prompt": "@ASPICE SPL-2 BP11 전문가 출시 산출물 간 일관성을 검증해줘.",
        "description": "출시 산출물 일관성 검증",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP11 일관성 보장",
    },
    {
        "id": "SPL2-BP12",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP12 출시 노트 제공",
        "agent": "ASPICE SPL-2 BP12 전문가",
        "prompt": "@ASPICE SPL-2 BP12 전문가 출시 노트가 패키지에 포함되었는지 확인하고 전달 매체 기록을 작성해줘.",
        "description": "출시 노트 패키지 포함 확인",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP12 출시 노트 제공",
    },
    {
        "id": "SPL2-BP13",
        "phase": "Phase 4.3",
        "title": "SPL.2.BP13 고객 전달",
        "agent": "ASPICE SPL-2 BP13 전문가",
        "prompt": "@ASPICE SPL-2 BP13 전문가 출시물을 고객에게 전달하고 수령 확인 기록을 작성해줘.",
        "description": "출시물 고객 전달 및 수령 확인",
        "expected_outputs": ["docs/SPL-2/"],
        "commit_msg": "docs(spl2): BP13 고객 전달 완료",
    },
]


# ══════════════════════════════════════════════════════════════════
#  메인 실행 로직
# ══════════════════════════════════════════════════════════════════

SEPARATOR = "═" * 70

def print_header():
    print(f"\n{SEPARATOR}")
    print(f"  ASPICE 프로세스 순차 실행기 (Clipboard 기반)")
    print(f"  총 {len(STEPS)}단계 | docs/aspice_workflow.md 기반")
    print(f"{SEPARATOR}\n")


def print_status(progress: dict):
    completed = set(progress.get("completed_steps", []))
    last = progress.get("last_step_index", -1)
    stopped_at = progress.get("last_stopped_at", "")
    print(f"\n{'─' * 60}")
    print(f"  진행 상황: {len(completed)}/{len(STEPS)} 완료")
    if progress.get("started_at"):
        print(f"  시작일: {progress['started_at']}")
    if stopped_at:
        print(f"  마지막 중단: {stopped_at}")

    next_index = last + 1
    if next_index < len(STEPS):
        next_step = STEPS[next_index]
        print(f"\n  ▶ 다음 실행 단계: [{next_step['phase']}] {next_index + 1}. {next_step['title']}")
        print(f"  💡 재개 명령어: python tools/aspice_runner.py --resume")
    else:
        print(f"\n  🎉 모든 단계가 완료되었습니다!")
    print(f"{'─' * 60}")

    current_phase = ""
    for i, step in enumerate(STEPS):
        if step["phase"] != current_phase:
            current_phase = step["phase"]
            print(f"\n  [{current_phase}]")
        status = "✓" if step["id"] in completed else ("▶" if i == last + 1 else " ")

        # 완료된 단계는 출력 폴더 파일 수 표시
        if step["id"] in completed:
            file_counts = []
            for expected in step["expected_outputs"]:
                path = PROJ_ROOT / expected
                if path.is_dir():
                    count = sum(1 for f in path.iterdir() if f.is_file())
                    file_counts.append(f"{Path(expected).name}({count}파일)")
            count_str = "  — " + ", ".join(file_counts) if file_counts else ""
        else:
            count_str = ""

        print(f"    [{status}] {i+1:2d}. {step['title']}{count_str}")
    print()


def run_step(index: int, step: dict, progress: dict):
    step_num = index + 1
    total = len(STEPS)

    print(f"\n{SEPARATOR}")
    print(f"  단계 {step_num}/{total}: {step['title']}")
    print(f"  Phase: {step['phase']}")
    print(f"  Agent: {step['agent']}")
    print(f"  설명: {step['description']}")
    print(f"{SEPARATOR}")

    # 0) 산출물 디렉토리 사전 생성
    create_step_directories(step)

    # 1) 이전 단계 커밋 여부 확인
    if not verify_clean_state(step["title"]):
        print(f"\n  💡 커밋 명령어: git add -A && git commit -m \"<메시지>\"")
        while True:
            resp = input("\n  커밋을 완료했으면 Enter, 자동 커밋하려면 'auto': ").strip()
            if resp.lower() == "auto":
                prev_msg = STEPS[index - 1]["commit_msg"] if index > 0 else "chore: initial state"
                git_commit(prev_msg)
                break
            elif resp == "":
                if not git_has_changes():
                    break
                print("  ⚠️  아직 변경사항이 남아있습니다.")
            else:
                print("  Enter 또는 'auto'를 입력하세요.")

    # 2) 프롬프트 처리
    if step["prompt"] is None:
        # 사람이 직접 작성하는 단계 (킥오프 등)
        print(f"\n  📝 이 단계는 사람이 직접 작성해야 합니다.")
        print(f"  예상 산출물: {', '.join(step['expected_outputs'])}")
        input(f"\n  작성을 완료했으면 Enter를 누르세요... ")
    else:
        # /clear 를 클립보드에 복사 → 사용자가 Chat에 붙여넣기
        print(f"\n  {'─' * 56}")
        print(f"  ⚠️  Copilot Chat 컨텍스트 초기화가 필요합니다.")
        copy_to_clipboard("/clear")
        print(f"  ✓ '/clear' 를 클립보드에 복사했습니다.")
        print(f"  👉 Chat 입력창에 Ctrl+V → Enter 하세요.")
        print(f"  {'─' * 56}")
        input(f"  /clear 완료 후 Enter... ")

        print(f"\n  📋 프롬프트를 클립보드에 복사합니다...")
        prompt_text = step["prompt"]
        if copy_to_clipboard(prompt_text):
            print(f"  ✓ 클립보드에 복사 완료!")
        else:
            print(f"\n  ─── 프롬프트 (수동 복사) ───")
            print(f"  {prompt_text}")
            print(f"  ─────────────────────────────")

        print(f"\n  👉 Copilot Chat에 Ctrl+V로 붙여넣고 실행하세요.")
        print(f"  👉 Agent가 산출물을 생성하면 Enter를 누르세요.")
        input(f"\n  Agent 작업 완료 후 Enter... ")

    # 3) 산출물 존재 확인
    print(f"\n  🔍 산출물 확인 중...")
    all_found = True
    for expected in step["expected_outputs"]:
        path = PROJ_ROOT / expected
        if path.exists():
            print(f"    ✓ {expected} — 존재함")
        else:
            print(f"    ✗ {expected} — 없음!")
            all_found = False

    if not all_found:
        resp = input("\n  일부 산출물이 누락되었습니다. 계속하시겠습니까? (y/n): ").strip()
        if resp.lower() != "y":
            print("  단계를 다시 실행하세요.")
            return False

    # 4) git 변경사항 확인 및 커밋 안내
    if git_has_changes():
        print(f"\n  📦 변경된 파일:")
        print(f"  {git_status_summary()}")
        print(f"\n  권장 커밋 메시지: {step['commit_msg']}")

        while True:
            resp = input("\n  커밋 방법 — 'auto': 자동 커밋 / 'manual': 직접 커밋 후 Enter / 'skip': 건너뛰기: ").strip()
            if resp.lower() == "auto":
                git_commit(step["commit_msg"])
                break
            elif resp.lower() == "manual":
                input("  직접 커밋 후 Enter를 누르세요... ")
                if not git_has_changes():
                    print("  ✓ 커밋 확인됨")
                    break
                else:
                    print("  ⚠️  아직 변경사항이 남아있습니다.")
            elif resp.lower() == "skip":
                print("  ⚠️  커밋을 건너뜁니다. 다음 단계 시작 전에 커밋이 필요합니다.")
                break
    else:
        print(f"\n  ℹ️  변경사항이 없습니다 (산출물이 이미 존재하는 경우).")

    # 5) 진행 상태 저장
    progress["completed_steps"].append(step["id"])
    progress["last_step_index"] = index
    save_progress(progress)
    print(f"\n  ✅ 단계 {step_num} 완료: {step['title']}")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ASPICE 프로세스 순차 실행기")
    parser.add_argument("--resume", action="store_true", help="마지막 완료 단계 이후부터 재개")
    parser.add_argument("--status", action="store_true", help="현재 진행 상황 확인")
    parser.add_argument("--step", type=int, help="특정 단계 번호부터 시작 (1-based)")
    parser.add_argument("--reset", action="store_true", help="진행 상태 초기화")
    args = parser.parse_args()

    print_header()
    progress = load_progress()

    if args.reset:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
        print("  진행 상태가 초기화되었습니다.")
        return

    if args.status:
        print_status(progress)
        return

    # 시작 인덱스 결정
    if args.step:
        start_index = args.step - 1
        if start_index < 0 or start_index >= len(STEPS):
            print(f"  ❌ 유효하지 않은 단계 번호: {args.step} (1~{len(STEPS)})")
            return
    elif args.resume:
        start_index = progress.get("last_step_index", -1) + 1
        if start_index >= len(STEPS):
            print("  🎉 모든 단계가 완료되었습니다!")
            return
        print(f"  ▶ 단계 {start_index + 1}부터 재개합니다.")
    else:
        start_index = 0
        # 진행 중인 작업이 있으면 재개 여부 확인
        last = progress.get("last_step_index", -1)
        if last >= 0:
            next_idx = last + 1
            stopped_at = progress.get("last_stopped_at", "알 수 없음")
            print(f"\n  ⚠️  진행 중인 작업이 감지되었습니다!")
            print(f"  마지막 완료: 단계 {last + 1} — {STEPS[last]['title']}")
            print(f"  중단 시각: {stopped_at}")
            if next_idx < len(STEPS):
                print(f"  다음 단계: [{STEPS[next_idx]['phase']}] {next_idx + 1}. {STEPS[next_idx]['title']}")
            resp = input("\n  [Enter] 중단 지점부터 재개 / [new] 처음부터 시작: ").strip().lower()
            if resp != "new":
                start_index = next_idx
                print(f"  ▶ 단계 {start_index + 1}부터 재개합니다.")

    if not progress.get("started_at"):
        progress["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 순차 실행
    for i in range(start_index, len(STEPS)):
        step = STEPS[i]
        success = run_step(i, step, progress)
        if not success:
            progress["last_stopped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_progress(progress)
            print(f"\n  ⏸  단계 {i+1}에서 중단되었습니다. --resume으로 재개하세요.")
            return

        if i < len(STEPS) - 1:
            resp = input(f"\n  다음 단계로 진행하시겠습니까? (Enter: 계속 / q: 종료): ").strip()
            if resp.lower() == "q":
                progress["last_stopped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_progress(progress)
                print(f"\n  ⏸  중단됨. 'python tools/aspice_runner.py --resume'으로 재개하세요.")
                return

    # 전체 완료
    print(f"\n{SEPARATOR}")
    print(f"  🎉 축하합니다! 전체 {len(STEPS)}단계가 완료되었습니다!")
    print(f"  ASPICE Phase 1~4 프로세스가 모두 수행되었습니다.")
    print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    main()
