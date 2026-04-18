---
name: gcc-test-build
description: "GCC/G++ + CMake + Google Test 빌드 환경 구성 및 테스트 실행 스킬. Use when: gcc 빌드 환경 설정, cmake 프로젝트 생성, gtest 테스트 실행, 단위 테스트 빌드, gcov lcov 커버리지 분석, C C++ 테스트 환경 구성, 테스트 빌드 실패 해결."
argument-hint: "대상 소스 디렉토리 또는 작업 내용을 설명하세요. 예: 'src/ 아래 모든 C 파일 테스트 빌드'"
---

# GCC/G++ + CMake + Google Test 빌드 환경 구성 스킬

## 개요

C/C++ 혼용 프로젝트에서 **CMake + Google Test** 기반 빌드 환경을 세팅하고, 테스트를 실행한 뒤 **gcov/lcov** 커버리지 리포트를 생성하는 전체 워크플로우를 제공합니다.

---

## 전제 조건 확인 (1단계)

터미널에서 아래 명령으로 필수 도구 존재 여부를 확인합니다:

```bash
gcc --version && g++ --version && cmake --version && gcov --version
```

누락된 항목이 있으면 아래 명령으로 설치합니다 (Ubuntu/Debian 기준):

```bash
sudo apt-get update && sudo apt-get install -y \
  build-essential cmake gcovr lcov \
  libgtest-dev googletest
```

> **macOS**: `brew install cmake gcovr lcov googletest`

---

## 프로젝트 구조 파악 (2단계)

현재 워크스페이스의 디렉토리 구조를 확인합니다:

- **소스 파일** 위치: `src/` 또는 소스 경로 확인
- **테스트 파일** 위치: `tests/` 또는 `test/` 확인
- **기존 CMakeLists.txt** 존재 여부 확인

기존 `CMakeLists.txt`가 없으면 [CMakeLists 템플릿](./assets/CMakeLists.txt.template)을 참고해 생성합니다.

---

## CMakeLists.txt 구성 (3단계)

Google Test 연동 및 커버리지 옵션이 포함된 `CMakeLists.txt`를 작성합니다.

핵심 포인트:

1. **언어 설정**: `project(<name> C CXX)` — C & C++ 혼용 선언
2. **표준 설정**: `CMAKE_C_STANDARD 11`, `CMAKE_CXX_STANDARD 17` (프로젝트에 맞게 조정)
3. **Google Test 연결**: `find_package(GTest REQUIRED)` 또는 `FetchContent`
4. **커버리지 플래그**: Debug 빌드에 `--coverage -fprofile-arcs -ftest-coverage` 추가
5. **테스트 등록**: `gtest_discover_tests()` 또는 `add_test()`

자세한 템플릿은 [assets/CMakeLists.txt.template](./assets/CMakeLists.txt.template)을 참조합니다.

---

## 빌드 디렉토리 생성 및 CMake 구성 (4단계)

```bash
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
```

빌드 타입별 차이:

| 옵션 | 커버리지 | 최적화 | 용도 |
|------|---------|--------|------|
| `Debug` | 가능 | 없음 | 테스트·커버리지 분석 |
| `Release` | 불가 | 최대 | 릴리스 산출물 |

---

## 빌드 실행 (5단계)

```bash
# build/ 디렉토리 내에서
cmake --build . --parallel $(nproc)
```

빌드 오류 발생 시:
- 컴파일 오류: 소스 파일 경로·헤더 include 경로 확인
- 링크 오류: `target_link_libraries`에 gtest, gtest_main 추가 여부 확인
- CMake 오류: CMake 버전 확인 (`cmake_minimum_required` 값 조정)

---

## 테스트 실행 (6단계)

```bash
# build/ 디렉토리 내에서 CTest로 실행
ctest --output-on-failure --verbose

# 또는 테스트 바이너리 직접 실행
./tests/<test_binary_name>
```

**Google Test 출력 해석:**

- `[ PASSED ]` — 성공
- `[ FAILED ]` — 실패 (메시지 확인 후 소스 수정)
- `[  SKIPPED ]` — 조건부 스킵

---

## 커버리지 리포트 생성 (7단계)

테스트 실행 후 `build/` 디렉토리에서:

```bash
# lcov로 커버리지 데이터 수집
lcov --capture --directory . --output-file coverage.info \
     --exclude '/usr/*' --exclude '*/gtest/*' --exclude '*/tests/*'

# HTML 리포트 생성
genhtml coverage.info --output-directory coverage_report

# 요약 출력
lcov --summary coverage.info
```

또는 gcovr로 간단하게:

```bash
gcovr --root .. --exclude '.*test.*' --html --html-details \
      -o coverage_report/index.html
gcovr --root .. --exclude '.*test.*'   # 터미널 요약
```

결과물: `build/coverage_report/index.html` — 브라우저로 열어 확인

---

## 체크리스트

- [ ] gcc/g++/cmake/gcov 설치 확인
- [ ] `CMakeLists.txt`에 `project(<name> C CXX)` 선언
- [ ] Google Test 연결 (`find_package` 또는 `FetchContent`)
- [ ] Debug 빌드에 `--coverage` 플래그 포함
- [ ] `enable_testing()` + `gtest_discover_tests()` 등록
- [ ] `cmake ..` 구성 성공
- [ ] `cmake --build .` 빌드 성공
- [ ] `ctest` 모든 테스트 통과
- [ ] `lcov`/`gcovr` 커버리지 리포트 생성 확인

---

## ASPICE 연계

| 커버리지 목표 | 관련 프로세스 |
|-------------|-------------|
| 문장 커버리지 ≥ 100% | SWE-4 단위 검증 |
| 분기 커버리지 ≥ 100% | SWE-4 단위 검증 |
| MC/DC | SWE-4 (안전 기능 적용 시) |
| 통합 테스트 커버리지 | SWE-5 통합 테스트 |

커버리지 결과는 ASPICE SWE-4 테스트 결과 기록(`SWE-TC-XXXX`)에 증거로 첨부합니다.
