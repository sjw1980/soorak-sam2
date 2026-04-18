---
name: git-commit
description: "Git 커밋 및 푸시 워크플로우 스킬. Use when: git 변경사항 커밋, staged 파일 정리, Conventional Commits 메시지 작성, git commit 후 push, 코드 변경 이력 남기기, 커밋 메시지 규칙 적용, ASPICE 산출물 변경 커밋."
argument-hint: "커밋할 내용을 간략히 설명하세요. 예: '요구사항 목록 추가'"
---

# Git Commit & Push 워크플로우

## 개요

이 스킬은 변경사항을 분석하고 Conventional Commits 형식의 커밋 메시지를 작성한 후 커밋 및 푸시를 수행합니다.
ASPICE 산출물과 연관된 변경은 커밋 메시지 본문에 관련 ID를 포함합니다.

---

## Conventional Commits 형식

```
<type>(<scope>): <subject>

[선택] <body> — 변경 이유, ASPICE ID 참조

[선택] <footer> — Breaking Change, 연관 이슈
```

### 허용 type

| type | 사용 상황 |
|------|----------|
| `feat` | 새 기능·산출물 추가 |
| `fix` | 버그·오류 수정 |
| `docs` | 문서·산출물 내용 변경 |
| `refactor` | 코드 구조 변경 (기능 유지) |
| `test` | 테스트 케이스 추가·수정 |
| `chore` | 빌드·설정 등 기타 변경 |
| `ci` | CI/CD 파이프라인 변경 |
| `style` | 포맷·스타일 변경 (동작 무관) |
| `perf` | 성능 개선 |

### scope 예시 (ASPICE 프로세스 기준)

`swe1`, `swe2`, `swe3`, `swe4`, `swe5`, `swe6`, `sup1`, `sup8`, `sup9`, `sup10`, `man3`, `config`, `ci`

---

## 절차

### 1단계 — 현재 상태 파악

`mcp_gitkraken_git_status` 도구로 변경된 파일 목록과 상태를 확인합니다.
- Untracked / Modified / Staged 파일을 분류합니다.
- 불필요한 파일(빌드 산출물, 임시파일)이 포함되지 않았는지 확인합니다.

### 2단계 — diff 검토

`mcp_gitkraken_git_log_or_diff` 도구로 변경 내용을 확인합니다.
- 변경된 파일의 실제 내용을 파악합니다.
- ASPICE 관련 산출물 ID(예: `SWE-REQ-0001`)가 있으면 메모합니다.

### 3단계 — 커밋 메시지 작성

아래 규칙을 따라 메시지를 작성합니다:

1. **subject** (필수): 50자 이하, 명령형, 마침표 없음
2. **body** (변경이 복잡하거나 ASPICE ID 참조 시): 72자 줄바꿈
   - ASPICE 산출물 관련 변경이면 `Refs: SWE-REQ-0001` 형태로 명시
3. **footer** (Breaking Change 또는 이슈 연결 시): `BREAKING CHANGE:` 또는 `Closes #N`

**예시:**
```
docs(swe1): 요구사항 목록 v1.1 갱신

SWE-REQ-0003 ~ 0007 신규 추가
SWE-REQ-0001 우선순위 변경 (High → Critical)

Refs: SWE-REQ-0001, SWE-REQ-0003
```

### 4단계 — 파일 스테이징 & 커밋

`mcp_gitkraken_git_add_or_commit` 도구를 사용합니다.
- 관련 없는 파일이 섞이지 않도록 파일 단위로 스테이징합니다.
- 논리적으로 한 묶음인 변경을 하나의 커밋에 포함합니다.

### 5단계 — Push

`mcp_gitkraken_git_push` 도구로 원격 저장소에 푸시합니다.
- 현재 브랜치와 원격 브랜치를 확인합니다.
- `--force` 옵션은 사용자 확인 후에만 사용합니다.

---

## 체크리스트

커밋 전 반드시 확인:

- [ ] 불필요한 파일(`.env`, 빌드 결과물, `*.log`)이 포함되지 않음
- [ ] 커밋 메시지 type이 올바름
- [ ] subject가 50자 이하이며 명령형
- [ ] ASPICE 산출물 변경 시 Refs 포함
- [ ] 논리적으로 분리 가능한 변경은 별도 커밋으로 분리

---

## 주의사항

- `git push --force` 또는 `git reset --hard`는 반드시 사용자에게 확인 후 실행합니다.
- 민감 정보(비밀번호, API 키)가 포함된 파일은 절대 커밋하지 않습니다.
- 공유 브랜치(`main`, `master`, `develop`)에 직접 커밋하는 경우 사용자에게 먼저 알립니다.
