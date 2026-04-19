# WP.17-11 — Grouped & Categorized Requirements (SWE-1 BP2)

Generated analysis: grouping, prioritization, categorization, and verification criteria for the requirements in `WP-17-11`.

## 목적

이 문서는 기존 `WP-17-11`의 요구사항을 SWE-1 BP2 관점에서 그룹화(카테고리화), 우선순위화하고, 각 요구사항에 대한 검증 기준(테스트/수행기준)을 제시한다.

---

## 분류 기준(요약)

- Functional: 기능적 동작 요구사항
- Input & Validation: 입력 파서·유효성 검사·오류 처리
- UX / REPL: 대화형 동작·사용자 명령·출력 포맷
- Non-Functional - Performance: 응답시간/성능
- Non-Functional - Resource: 메모리/자원 목표
- Portability & Environment: 운영환경·이식성
- Security: 입력 검증·침해 방어
- Quality & Testability: 테스트·정적분석·추적성

---

## 요약 테이블

| REQ ID       | 요약 설명                                              | 카테고리                     | 우선순위 | 검증 기준 (Acceptance / Test)                                                                                                                                          |
| ------------ | ------------------------------------------------------ | ---------------------------- | -------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SWE-REQ-0001 | 사칙연산(+, -, ×, ÷) 정확 계산                         | Functional                   |     High | Unit tests covering +,-,\*,/ with integer and float vectors; expected exact/within-tolerance results; all tests pass.                                                  |
| SWE-REQ-0002 | 부동소수점 입력 지원 및 적절 정밀도                    | Functional                   |     High | Unit tests with float cases; numeric comparison within relative error ≤ 1e-9 or match formatted 6 decimal places; pass.                                                |
| SWE-REQ-0003 | 0으로 나누기 처리, 명확한 에러 메시지, 비정상종료 방지 | Input & Validation           |     High | Unit test dividing by zero → function returns error flag + message containing "divide"/"zero"; REPL stays active; no uncaught exceptions.                              |
| SWE-REQ-0004 | 제곱근·지수 연산 지원                                  | Functional                   |   Medium | Unit tests for `sqrt` and `pow` (positive/negative/edge cases); negative sqrt → handled error; results validated.                                                      |
| SWE-REQ-0005 | REPL 루프, 프롬프트 "> ", `quit`/`exit` 정상종료       | UX / REPL                    |     High | Integration test: spawn REPL, observe prompt "> "; send `quit`/`exit` → process exits with code 0.                                                                     |
| SWE-REQ-0006 | 입력 유효성 검사, 잘못된 입력 안내                     | Input & Validation           |     High | Unit tests with malformed inputs → returns/prints "Invalid input" (or equivalent); no crash.                                                                           |
| SWE-REQ-0007 | 결과 포매팅: 기본 소수 6자리(설정 가능)                | UX / REPL                    |   Medium | Unit tests: numeric outputs formatted to 6 decimals by default; configurable option verified.                                                                          |
| SWE-REQ-0008 | `help` 명령 제공                                       | UX / REPL                    |      Low | Integration test: `help` prints supported ops and examples; contains minimal required keywords.                                                                        |
| SWE-REQ-0009 | 주요 오류 로그 기록(콘솔 또는 파일)                    | Quality & Testability        |      Low | Trigger errors (parse, calc) → verify log contains timestamp, REQ ID or context, and message.                                                                          |
| SWE-REQ-0010 | 적절한 종료 코드(성공 0, 오류 >0)                      | UX / REPL                    |      Low | Run program with normal and error exit paths; assert exit codes (0 for normal quit, >0 for fatal error).                                                               |
| SWE-REQ-0011 | 단일 연산 응답시간 < 100ms (목표)                      | Non-Functional - Performance |     High | Benchmark test under CI/dev machine: mean latency per op < 100ms for representative cases (document test environment).                                                 |
| SWE-REQ-0012 | 런타임 메모리 목표: 64KB 이하(목표)                    | Non-Functional - Resource    |   Medium | Memory profiling run; record RSS/heap. Note: Python runtime may not meet 64KB — treat as "목표"; verification: measure and document, provide justification if not met. |
| SWE-REQ-0013 | Windows/Linux, Python 3.10+ 지원                       | Portability & Environment    |     High | CI matrix: run smoke test on Windows and Linux images using Python 3.10; all smoke tests pass.                                                                         |
| SWE-REQ-0014 | 입력을 불신하고 검증(주입 차단)                        | Security                     |     High | Fuzzing and crafted-input tests (e.g., long strings, shell characters) → no code execution; static scan for `eval`/`exec`; acceptance: no unsafe execution path.       |
| SWE-REQ-0015 | 단위 테스트 분기 커버리지 ≥ 90%                        | Quality & Testability        |     High | Coverage run (coverage.py) showing branch coverage ≥ 90% on main branch; failing if below.                                                                             |
| SWE-REQ-0016 | 정적분석 주요 경고 릴리스 전 해결                      | Quality & Testability        |   Medium | Run Pylint/Flake8; critical severity issues = 0 (or documented exception); report attached.                                                                            |
| SWE-REQ-0017 | 요구사항 ↔ 테스트 양방향 추적성 보유                   | Quality & Testability        |     High | Traceability matrix exists linking each SWE-REQ to tests (unit/integration/ITC); 100% mapping verified.                                                                |

---

## 권장 검증 방법(간단 가이드)

- 단위 테스트: `pytest` + `coverage` 사용
  - 테스트 범위: 파서, 계산기(core calc functions), REPL 핸들러, 에러 핸들링
  - Branch coverage 목표: `coverage xml`/badge로 90% 이상
- 통합 테스트: REPL 프로세스를 스폰(pexpect / subprocess)하여 프롬프트·명령·종료 동작 확인
- 성능 테스트: 마이크로벤치마크(예: `timeit` 또는 pytest-benchmark)로 평균 응답시간 측정
- 메모리/자원 측정: CI에서 `psutil` 또는 OS 도구(RSS 측정)로 반복 실행 중 메모리 사용량 로깅
- 보안/입력 검증: 단순한 fuzz 테스트(랜덤 입력/특수문자)와 정적분석으로 잠재적 `eval` 사용 여부 점검
- 로깅: 표준 로그 포맷(타임스탬프, 레벨, 컴포넌트, 메시지)으로 기록하고, 오류 시 로그 항목 존재 검증
- 추적성: 요구사항별로 테스트케이스 ID를 부여하고 `tests/traceability.md` 또는 CI 아티팩트로 유지

---

## 권장 테스트 케이스 예시 (요약)

- SWE-REQ-0001: 기본 연산 벡터(1+1=2, 2\*3=6, 5-7=-2, 8/4=2)
- SWE-REQ-0002: 소수 입력 예제(0.1+0.2 등) 및 허용 오차 검사
- SWE-REQ-0003: `1/0` 입력 → 사용자 친화적 메시지, 예외 미발생
- SWE-REQ-0005: REPL: 확인 프롬프트, `quit` → exit 0
- SWE-REQ-0011: 1000회 연산 반복 → 평균 응답시간 측정
- SWE-REQ-0014: 입력에 `; rm -rf /` 또는 백틱 포함 → 프로그램 내부에서 실행되지 않음
- SWE-REQ-0015: coverage 측정 스크립트 실행 및 리포트 생성

---

## 권장 산출물(검증 산출물)

- `tests/` : 단위 및 통합 테스트 코드
- `coverage/` : 커버리지 리포트(HTML/XML)
- `logs/` : 테스트 실행 시 오류 로그(샘플)
- `tests/traceability.md` : 요구사항 ↔ 테스트 매핑표
- `ci/` : CI 워크플로우(Windows/Linux matrix) 정의

---

## 비고(현실적 고려 사항)

- `SWE-REQ-0012`의 메모리 목표(64KB)는 Python 런타임에서 현실적이지 않을 수 있으므로 "목표"로 유지하고, Python 사용 시 실제 소비량 측정 후 근거 문서를 첨부하여 승인 절차를 권장한다.
- 성능/메모리 목표는 테스트 환경(하드웨어, OS, Python 빌드)에 따라 달라지므로, 각 검증 리포트에 환경(명세)을 반드시 기록해야 한다.

---

Generated by ASPICE SWE-1 BP2 analysis (AI-assisted). 원문 요구사항은 [WP.17-11](../WP-17-11.md).
