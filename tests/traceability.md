# Traceability Matrix — 요구사항 ↔ 테스트 매핑

이 문서는 `WP-17-11`에 정의된 소프트웨어 요구사항과 권장 테스트케이스의 매핑을 제공합니다. 각 요구사항에 대해 권장 테스트 유형, 권장 테스트 파일(경로), 그리고 수락 기준을 제시합니다.

| Requirement ID | Test ID     | Test Type             | Test File / Target                                                                              | Acceptance Criteria                                                                          |
| -------------- | ----------- | --------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| SWE-REQ-0001   | SWE-TC-0001 | Unit                  | tests/test_calculator_functions.py::test_basic_arithmetic                                       | 정수/실수 케이스 포함; 결과가 기대값(또는 허용오차)과 일치함                                 |
| SWE-REQ-0002   | SWE-TC-0002 | Unit                  | tests/test_calculator_functions.py::test_float_precision                                        | 다양한 부동소수점 케이스; 상대오차 ≤ 1e-9 또는 출력 포맷(6소수점)과 일치                     |
| SWE-REQ-0003   | SWE-TC-0003 | Unit + Integration    | tests/test_error_handling.py::test_divide_by_zero; tests/test_repl.py::test_divide_by_zero_repl | 나눗셈 0 처리 시 함수는 에러플래그+메시지 반환; REPL은 계속 실행되고 uncaught exception 없음 |
| SWE-REQ-0004   | SWE-TC-0004 | Unit                  | tests/test_math_functions.py::test_sqrt_pow                                                     | sqrt/pow에 대한 정상/경계/예외 케이스 검증; 음수 sqrt는 적절히 에러 처리됨                   |
| SWE-REQ-0005   | SWE-TC-0005 | Integration           | tests/test_repl.py::test_repl_prompt_and_quit                                                   | REPL 프롬프트 `"> "` 표시; `quit`/`exit` 입력 시 프로세스 종료 코드 0 반환                   |
| SWE-REQ-0006   | SWE-TC-0006 | Unit                  | tests/test_input_parser.py::test_invalid_inputs                                                 | 잘못된 입력에 대해 명확한 안내(예: "Invalid input") 출력; 크래시 없음                        |
| SWE-REQ-0007   | SWE-TC-0007 | Unit                  | tests/test_output_format.py::test_default_formatting                                            | 기본 출력이 소수점 6자리 포맷; 설정 변경 시 포맷 변경 확인                                   |
| SWE-REQ-0008   | SWE-TC-0008 | Integration           | tests/test_repl.py::test_help_command                                                           | `help` 명령 실행 시 지원 연산 및 사용 예시 출력                                              |
| SWE-REQ-0009   | SWE-TC-0009 | Logging Test          | tests/test_logging.py::test_error_logging                                                       | 오류 발생 시 로그(타임스탬프, 레벨, 컴포넌트 포함) 항목이 기록됨                             |
| SWE-REQ-0010   | SWE-TC-0010 | Integration           | tests/test_exit_codes.py::test_exit_codes                                                       | 정상 종료는 exit code 0, 오류 경로는 >0 반환                                                 |
| SWE-REQ-0011   | SWE-TC-0011 | Performance Benchmark | benchmarks/benchmark_latency.py                                                                 | 대표 케이스 평균 응답시간 < 100ms (테스트 환경 명세 포함)                                    |
| SWE-REQ-0012   | SWE-TC-0012 | Resource Profiling    | benchmarks/memory_profile.py                                                                    | 메모리 사용량(예: RSS) 측정 및 기록; Python 환경에서 목표(64KB) 미달성 시 근거 문서 첨부     |
| SWE-REQ-0013   | SWE-TC-0013 | CI Smoke Tests        | ci/workflows/smoke.yml / smoke scripts                                                          | Windows/Linux, Python3.10 매트릭스에서 스모크 테스트 통과                                    |
| SWE-REQ-0014   | SWE-TC-0014 | Security / Fuzz       | tests/test_security_fuzz.py                                                                     | 퍼즈/특수입력으로 코드 실행 경로 없음; 정적분석에서 `eval`/`exec` 등 위험 호출 없음          |
| SWE-REQ-0015   | SWE-TC-0015 | Coverage Check        | ci scripts / coverage report                                                                    | Branch coverage ≥ 90% (CI 리포트)                                                            |
| SWE-REQ-0016   | SWE-TC-0016 | Static Analysis       | ci lint job                                                                                     | Pylint/Flake8 critical 경고 0건(혹은 문서화된 예외만 허용)                                   |
| SWE-REQ-0017   | SWE-TC-0017 | Traceability Check    | tests/traceability.md                                                                           | 요구사항 ↔ 테스트 매핑이 100% 충족됨                                                         |

---

Notes:

- 테스트 파일/케이스는 권장 네이밍과 위치입니다. 원하시면 각 항목에 대한 테스트 스켈레톤(파일+기본 테스트 함수)을 자동 생성해 드립니다.

Generated artifact: this file is the canonical requirements→tests traceability matrix for `WP-17-11`.
