"""
260414_aspice_workflow.md 파일에서 WP ID를 추출하는 스크립트.
각 WP ID가 어떤 프로세스 섹션에서 사용되는지 함께 출력한다.
"""

import re
from pathlib import Path
from collections import defaultdict

MD_FILE = Path(__file__).parent / "260414_aspice_workflow.md"

# WP ID 패턴: WP.XX-YY 형식
WP_PATTERN = re.compile(r"WP\.(\d{2}-\d{2})")

# 섹션 헤더 (# 로 시작하는 줄)
SECTION_PATTERN = re.compile(r"^# (.+)")


def extract_wp_ids(filepath: Path) -> dict[str, list[str]]:
    """
    Returns:
        { "WP.XX-YY": ["섹션명", ...] }
    """
    wp_to_sections: dict[str, set[str]] = defaultdict(set)
    current_section = "(없음)"

    with filepath.open(encoding="utf-8") as f:
        for line in f:
            section_match = SECTION_PATTERN.match(line)
            if section_match:
                current_section = section_match.group(1).strip()

            for wp_num in WP_PATTERN.findall(line):
                wp_id = f"WP.{wp_num}"
                wp_to_sections[wp_id].add(current_section)

    # set → sorted list
    return {wp: sorted(secs) for wp, secs in sorted(wp_to_sections.items())}


def main():
    if not MD_FILE.exists():
        print(f"파일을 찾을 수 없습니다: {MD_FILE}")
        return

    result = extract_wp_ids(MD_FILE)

    print(f"총 {len(result)}개의 고유 WP ID 발견\n")
    print(f"{'WP ID':<14} {'사용 섹션'}")
    print("-" * 80)
    for wp_id, sections in result.items():
        print(f"{wp_id:<14} {' / '.join(sections)}")

    print("\n--- 고유 WP ID 목록 (정렬) ---")
    print(", ".join(result.keys()))


if __name__ == "__main__":
    main()
