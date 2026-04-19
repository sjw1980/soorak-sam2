# ASPICE AI Agent 프로젝트 — 시작 가이드

> **Automotive SPICE PAM 3.1** 기반 소프트웨어 개발 프로세스를 AI Agent로 자동화하는 프로젝트입니다.  
> 88개 BP-Level Agent가 순차적으로 산출물을 생성하고, 형상 관리(Git)와 연동하여 추적성을 보장합니다.

---

## 📋 목차

1. [프로젝트 구조](#프로젝트-구조)
2. [사전 준비](#사전-준비)
3. [시작하기](#시작하기)
4. [워크플로우 개요](#워크플로우-개요)
5. [실행기 사용법](#실행기-사용법)
6. [형상 관리 규칙](#형상-관리-규칙)
7. [문서 체계](#문서-체계)

---

## 프로젝트 구조

```
soorak-sam2/
├── .github/
│   ├── agents/                    # 88개 BP Agent + 12개 상위 Agent
│   │   ├── aspice-man3-bp1.agent.md
│   │   ├── aspice-swe1-bp1.agent.md
│   │   └── ...
│   ├── copilot-instructions.md    # 프로젝트 공통 지침
│   └── skills/                    # 빌드·커밋 스킬
├── docs/
│   ├── PROJECT-KICKOFF.md         # ⭐ 킥오프 문서 (사람이 먼저 작성)
│   ├── aspice_workflow.md         # 워크플로우 정의 (Phase 1~6)
│   ├── aspice_wp_overview.md      # 작업 산출물(WP) 개요
│   ├── wp-templates/              # 44개 WP 양식 템플릿
│   │   ├── WP-04-04-sw-architecture.md
│   │   ├── WP-08-12-project-plan.md
│   │   └── ...
│   ├── MAN-3/                     # (생성됨) 프로젝트 관리 산출물
│   ├── SWE-1/ ~ SWE-6/           # (생성됨) SW 엔지니어링 산출물
│   ├── SUP-1/ SUP-8/ SUP-9/ SUP-10/  # (생성됨) 지원 프로세스 산출물
│   └── SPL-2/                     # (생성됨) 제품 릴리스 산출물
├── src/                           # 소스 코드 (SWE.3.BP8에서 생성)
├── tests/                         # 테스트 코드 (SWE.4.BP4에서 생성)
├── tools/
│   ├── aspice_runner.py           # ⭐ ASPICE 프로세스 순차 실행기
│   ├── aspice_to_html.py
│   └── extract_wp_ids.py
└── .aspice-progress.json          # (자동 생성) 진행 상태 추적
```

---

## 사전 준비

### 필수 도구

| 도구               | 버전  | 용도                         |
| ------------------ | ----- | ---------------------------- |
| **Python**         | 3.8+  | 실행기 스크립트 구동         |
| **Git**            | 2.20+ | 형상 관리                    |
| **VS Code**        | 최신  | AI Agent 실행 환경           |
| **GitHub Copilot** | 최신  | Agent 모드에서 BP Agent 호출 |

### 초기 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd soorak-sam2

# 2. Git 초기 설정 확인
git status

# 3. Python 확인 (외부 패키지 불필요)
python --version
```

> **참고**: `aspice_runner.py`는 Python 표준 라이브러리만 사용합니다 (외부 패키지 설치 불필요).

---

## 시작하기

### Step 1: 킥오프 문서 작성

**가장 먼저** `docs/PROJECT-KICKOFF.md`를 작성합니다. 이 문서는 AI Agent가 대체할 수 없는, **사람이 직접 결정해야 할 항목**입니다.

```bash
# 킥오프 템플릿 열기
code docs/PROJECT-KICKOFF.md
```

작성해야 할 항목:

- 제품 비전 (제품명, 개요, 목표 사용자)
- 기술 플랫폼 (언어, 빌드 시스템, 테스트 프레임워크)
- 프로젝트 제약 사항 (ASPICE 목표 수준, 규제, 일정)
- 초기 요구사항 (기능적/비기능적)
- 형상 관리 방식
- 품질 기준
- 출시 전략
- 승인 권한자

### Step 2: 실행기 시작

```bash
# 전체 프로세스 순차 실행
python tools/aspice_runner.py
```

실행기가 하는 일:

1. **프롬프트를 클립보드에 복사** — 각 단계의 Agent 프롬프트가 자동 복사됩니다
2. **사용자가 AI에 붙여넣기** — VS Code Copilot Chat에 `Ctrl+V`로 붙여넣고 실행
3. **산출물 확인** — Agent가 생성한 파일의 존재 여부를 자동 확인
4. **Git 커밋 안내** — 권장 커밋 메시지 제공 + 자동/수동 커밋 선택

### Step 3: 반복

Phase 1(계획) → Phase 2(환경) → Phase 3(엔지니어링) → Phase 4(출시) 순서로 진행됩니다.  
총 **65단계**가 정의되어 있으며, 중간에 종료 후 `--resume`으로 재개할 수 있습니다.

---

## 워크플로우 개요

```
Phase 1 (계획)
├── 1.1 프로젝트 정의    MAN.3.BP1 → BP2 → BP3
├── 1.2 지원 전략 수립    SUP.8.BP1 → SUP.1.BP1 → SUP.9.BP1 → SUP.10.BP1
├── 1.3 테스트 전략       SWE.4.BP1 → SWE.5.BP1 → SWE.5.BP2 → SWE.6.BP1
└── 1.4 WBS              MAN.3.BP4

Phase 2 (환경 구축)
└── SUP.8.BP2 → SUP.8.BP3 → SUP.1.BP2

Phase 3 (SW 엔지니어링)
├── SWE.1 요구사항       BP1~BP7 → SUP.8.BP4 (요구사항 베이스라인)
├── SWE.2 아키텍처       BP1~BP8 → SUP.8.BP4 (아키텍처 베이스라인)
├── SWE.3 상세설계/코딩  BP1~BP6, BP8
├── SWE.4 단위 검증      BP2~BP6
├── SWE.5 통합           BP3~BP8
└── SWE.6 적격성 테스트  BP2~BP6

Phase 4 (출시/배포)
├── 4.1 QA/형상 감사     SUP.1.BP3 → SUP.8 (BP8,BP5,BP9,BP6,BP7)
├── 4.2 출시 준비        SPL.2.BP1~BP5
└── 4.3 배포             SPL.2.BP7~BP13
```

> **Phase 5** (버그 처리)와 **Phase 6** (변경 요청 처리)은 필요 시 별도로 실행합니다.

---

## 실행기 사용법

### 기본 명령어

```bash
# 처음부터 시작
python tools/aspice_runner.py

# 마지막 완료 단계 이후부터 재개
python tools/aspice_runner.py --resume

# 현재 진행 상황 확인
python tools/aspice_runner.py --status

# 특정 단계부터 시작 (예: 12번째 단계)
python tools/aspice_runner.py --step 12

# 진행 상태 초기화
python tools/aspice_runner.py --reset
```

### 실행 흐름

```
┌─────────────────────────────────────┐
│ 1. git status 확인 (clean 상태?)     │
│    └── dirty → 커밋 유도             │
├─────────────────────────────────────┤
│ 2. Agent 프롬프트 → 클립보드 복사    │
├─────────────────────────────────────┤
│ 3. 사용자: AI에 붙여넣기 → 실행     │
├─────────────────────────────────────┤
│ 4. 산출물 존재 확인                  │
├─────────────────────────────────────┤
│ 5. git commit (auto/manual/skip)    │
├─────────────────────────────────────┤
│ 6. 다음 단계 진행 여부 확인          │
└─────────────────────────────────────┘
```

### 클립보드에 복사되는 프롬프트 예시

```
@ASPICE MAN-3 BP1 전문가 docs/PROJECT-KICKOFF.md 를 읽고
프로젝트 범위 정의서를 작성해줘. 프로젝트 계획서(MAN3-PP-0001)
초안을 docs/MAN-3/ 에 생성해줘.
```

이 프롬프트를 VS Code Copilot Chat의 **Agent 모드**에 붙여넣으면, 해당 BP 전문 Agent가 자동으로 산출물을 생성합니다.

---

## 형상 관리 규칙

### 커밋 규칙

각 단계마다 **반드시 커밋**한 뒤 다음 단계로 진행합니다.

```bash
# 커밋 메시지 형식 (Conventional Commits)
docs(<scope>): <설명>    # 문서 산출물
feat(<scope>): <설명>    # 코드 구현
test(<scope>): <설명>    # 테스트 코드

# 예시
docs(man3): BP1 프로젝트 범위 정의 — MAN3-PP-0001 초안
docs(swe1): BP1 SW 요구사항 명세
feat(swe3): BP8 SW 유닛 구현
test(swe4): BP4 단위 테스트 수행
```

### 왜 매 단계마다 커밋하는가?

- **추적성**: ASPICE는 모든 산출물의 변경 이력을 요구합니다
- **베이스라인**: SWE.1, SWE.2, SWE.5 완료 시 SUP.8.BP4로 베이스라인 설정
- **복구 가능**: 문제 발생 시 특정 단계로 되돌릴 수 있습니다
- **감사 증적**: 형상 감사 시 각 커밋이 BP 활동의 증거가 됩니다

---

## 문서 체계

### ID 체계

```
<프로세스>-<유형>-<4자리 일련번호>
예: SWE-REQ-0001, MAN3-PP-0001, SUP8-CI-0001
```

### WP 템플릿

`docs/wp-templates/` 폴더에 44개의 작업 산출물 양식이 준비되어 있습니다.  
Agent는 이 템플릿을 참조하여 규격에 맞는 산출물을 자동으로 생성합니다.

| WP 범주  | 예시        | 설명                            |
| -------- | ----------- | ------------------------------- |
| WP.04-xx | 설계서      | SW 아키텍처/상세 설계           |
| WP.08-xx | 계획서      | 프로젝트 계획, 시험 계획 등     |
| WP.11-xx | 제품 산출물 | 출시 정보, 패키지 등            |
| WP.13-xx | 기록        | 추적성, 검토 기록, 변경 통제 등 |
| WP.17-xx | 명세서      | 요구사항, 시험 명세 등          |

---

## FAQ

**Q: 외부 AI (ChatGPT 등)에서도 사용할 수 있나요?**  
A: 네. 클립보드에 복사된 프롬프트를 아무 AI에 붙여넣으면 됩니다. 다만 `@Agent명` 부분은 VS Code Agent 모드 전용이므로, 외부 AI 사용 시 Agent 이름 부분은 지시사항의 맥락으로 전달하세요.

**Q: 도중에 종료했다가 다시 시작하려면?**  
A: `python tools/aspice_runner.py --resume`으로 마지막 완료 단계 이후부터 재개됩니다.

**Q: Phase 5/6 (버그·변경요청)은 언제 실행하나요?**  
A: Phase 4 완료 후 필요 시 해당 Agent를 직접 호출합니다. 예: `@ASPICE SUP-9 BP2 전문가 결함 보고서 작성해줘`

**Q: 킥오프 문서 없이 시작할 수 있나요?**  
A: 아니오. `PROJECT-KICKOFF.md`는 Agent의 입력 데이터입니다. 미작성 시 Agent가 임의로 가정하게 되어 산출물 품질이 떨어집니다.
