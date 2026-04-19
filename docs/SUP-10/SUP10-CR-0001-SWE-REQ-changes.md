Document ID : SUP10-CR-0001
Version : v1.0 / 2026-04-19
Status : Draft
Related WP : WP-13-21 (Change Control Record)
Author : ASPICE SWE-1 BP3 전문가 (auto-generated)

Title: 변경 요청 — SWE-REQ-0002, SWE-REQ-0011, SWE-REQ-0012, SWE-REQ-0003 (에러 포맷)

Summary:

- 본 CR은 `docs/SWE-1/WP-17-11.md`에 정의된 다음 요구사항의 명확화 및 변경을 요청합니다:
  - SWE-REQ-0002 (부동소수점 정밀도): 측정·검증 방법 및 허용오차 규정 추가
  - SWE-REQ-0011 (성능 응답시간): 벤치마크 환경·측정 방식 정의
  - SWE-REQ-0012 (메모리 목표 64KB): Python 환경에서의 현실성 검토 및 "목표" 표기 또는 언어 변경 검토
  - SWE-REQ-0003 (0으로 나누기 처리): 에러 메시지/반환 규격(성공 bool + errorMsg) 표준화

Rationale / Justification:

- WP-15-01 분석 결과에 따라 위 항목들은 현재 문서화 수준으로는 구현 및 검증이 어렵거나(메모리), 측정·검증 재현성이 낮아 심사·검증 단계에서 불필요한 이슈를 발생시킬 우려가 있습니다.

Requested Changes (proposed wording / actions):

1. SWE-REQ-0002 (정밀도)

   - Proposed: "부동소수점 연산 결과는 IEEE-754 double (Python float) 기반으로 계산하며, 비교는 상대오차(relative error) ≤ 1e-9을 기본 허용 오차로 한다. 금융/정밀 연산 요구가 있는 경우 `decimal` 모듈을 사용하고 별도 요구사항으로 명시한다."
   - Impact: 단위 테스트에 허용오차 항목 추가. 개발 impact: Low.

2. SWE-REQ-0011 (성능)

   - Proposed: "성능 검증은 지정된 테스트 환경(예: GitHub Actions ubuntu-latest runner, 2 vCPU, 8GB RAM, Python 3.10)에서 수행하며, 측정은 N=1000 반복 기준 P50 및 P95를 보고한다. 합격 기준: P50 < 100ms."
   - Impact: 벤치마크 구현 및 CI 단계 추가. Development impact: Low–Medium (CI jobs).

3. SWE-REQ-0012 (메모리)

   - Proposed: "런타임 메모리 목표(64KB)는 '목표'로 유지하되, Python(CPython) 기반 구현의 현실성을 고려하여 POC(메모리 프로파일) 결과를 제출하고, 필요 시 언어/런타임 변경을 권고한다. 64KB를 강제할 경우 C/C++로의 재구현 필요성을 명시한다."
   - Impact: If kept mandatory → Significant schedule and resource impact (High). Otherwise → Low.

4. SWE-REQ-0003 (에러 포맷)
   - Proposed: "계산 API는 항상 `OperationResult` 형식(예: `{ success: bool, errorMsg: str, value: Optional[float] }`)을 반환하며, 0으로 나누기 시 `success=false`와 `errorMsg='divide by zero'`를 반환한다. REPL은 에러 발생 후 세션을 유지한다."
   - Impact: Minor code change; consistent API and tests.

Affected Documents / Systems:

- docs/SWE-1/WP-17-11.md (SRS)
- docs/SWE-1/WP-15-01-analysis-report.md (analysis)
- docs/wp-templates/WP-17-50.md (verification criteria)
- tests/ (test cases)

Estimated Schedule Impact:

- Minor wording changes + WP-17-50 updates: 0.5–1 PD
- CI benchmark job + tests: 1–2 PD
- If 64KB mandatory and language change required: +10–30 PD (TBD after feasibility study)

Risk Assessment:

- Not applying these clarifications risks failed verification attempts and repeated review comments during ASPICE assessments.

Approval
| CR ID | Related REQ(s) | Requested By | Date | Status |
|-------|----------------|--------------|------------|--------|
| SUP10-CR-0001 | SWE-REQ-0002, SWE-REQ-0011, SWE-REQ-0012, SWE-REQ-0003 | ASPICE SWE-1 BP3 agent | 2026-04-19 | Draft |

Next Steps:

- Review and approval by Requirement Owner and Project Lead.
- Upon approval, update `docs/SWE-1/WP-17-11.md` via formal change request procedure and update `WP-17-50` and test artifacts.
