#!/usr/bin/env python3
"""aspice_linkify.py

Phase 1: Add <a id="ID"></a> HTML anchors at the definition point of every
          content-level ID in its owning document.
Phase 2: Replace every bare ID reference in all .md files under docs/ with a
          markdown hyperlink  [ID](relative-path#ID)  pointing to that anchor.

Document-level IDs (SWE4-TC-SPEC-0001, MAN3-PP-0001, etc.) are linked to the
file top (no per-document anchor needed).
"""

import re
import os
from pathlib import Path

DOCS_DIR = Path(r"d:\Works\soorak-sam\docs")

# -----------------------------------------------------------------------
# 1.  Content (item-level) IDs  →  (subfolder, filename)
# -----------------------------------------------------------------------
CONTENT_ID_TO_DEF: dict[str, tuple[str, str]] = {
    "SWE-REQ":  ("SWE-1", "SWE-1-requirements.md"),
    "SWE-COMP": ("SWE-2", "SWE2-ARCH-0001-software-architecture.md"),
    "SWE-IF":   ("SWE-2", "SWE2-ARCH-0001-software-architecture.md"),
    "SWE-UNIT": ("SWE-3", "SWE3-UNIT-SPEC-0001-unit-design.md"),
    "SWE-TC":   ("SWE-4", "SWE4-TC-SPEC-0001-unit-test.md"),
    "SWE-ITC":  ("SWE-5", "SWE5-ITC-SPEC-0001-integration-test.md"),
    "SWE-QTC":  ("SWE-6", "SWE6-QTC-SPEC-0001-qualification-test.md"),
    "MAN3-RSK":  ("MAN-3", "MAN3-PP-0001-project-plan.md"),
    "MAN3-WBS":  ("MAN-3", "MAN3-PP-0001-project-plan.md"),
    "MAN3-MS":   ("MAN-3", "MAN3-PP-0001-project-plan.md"),
    "MAN3-ISS":  ("MAN-3", "MAN3-PP-0001-project-plan.md"),
    "PROJ-GOAL": ("SWE-1", "SWE1-TRACE-0001-traceability-review.md"),
}

# -----------------------------------------------------------------------
# 2.  Document-level IDs  →  (subfolder, filename)
# -----------------------------------------------------------------------
DOC_ID_TO_FILE: dict[str, tuple[str, str]] = {
    "SWE1-REQ-SPEC-0001":  ("SWE-1", "SWE-1-requirements.md"),
    "SWE2-ARCH-0001":      ("SWE-2", "SWE2-ARCH-0001-software-architecture.md"),
    "SWE3-UNIT-SPEC-0001": ("SWE-3", "SWE3-UNIT-SPEC-0001-unit-design.md"),
    "SWE4-TC-SPEC-0001":   ("SWE-4", "SWE4-TC-SPEC-0001-unit-test.md"),
    "SWE5-ITC-SPEC-0001":  ("SWE-5", "SWE5-ITC-SPEC-0001-integration-test.md"),
    "SWE6-QTC-SPEC-0001":  ("SWE-6", "SWE6-QTC-SPEC-0001-qualification-test.md"),
    "SWE1-TRACE-0001":     ("SWE-1", "SWE1-TRACE-0001-traceability-review.md"),
    "SWE2-TRACE-0001":     ("SWE-2", "SWE2-TRACE-0001-traceability-review.md"),
    "SWE3-TRACE-0001":     ("SWE-3", "SWE3-TRACE-0001-traceability-review.md"),
    "SWE4-TRACE-0001":     ("SWE-4", "SWE4-TRACE-0001-traceability-review.md"),
    "SWE5-TRACE-0001":     ("SWE-5", "SWE5-TRACE-0001-traceability-review.md"),
    "SWE6-TRACE-0001":     ("SWE-6", "SWE6-TRACE-0001-traceability-review.md"),
    "MAN3-PP-0001":        ("MAN-3", "MAN3-PP-0001-project-plan.md"),
    "SPL2-BUILD-0001":     ("SPL-2", "SPL2-BUILD-0001-build-environment.md"),
    "SPL2-FEAT-0001":      ("SPL-2", "SPL2-FEAT-0001-feature-model.md"),
    "SPL2-REL-0001":       ("SPL-2", "SPL2-REL-0001-release-note.md"),
    "SPL2-TRACE-0001":     ("SPL-2", "SPL2-TRACE-0001-traceability-review.md"),
    "SUP1-QAR-0001":       ("SUP-1", "SUP1-QAR-0001-qa-audit-report.md"),
    "SUP8-CI-LIST-0001":   ("SUP-8", "SUP8-CI-LIST-0001-ci-baseline.md"),
    "SUP8-CMP-0001":       ("SUP-8", "SUP8-CMP-0001-cm-plan.md"),
    "SUP9-PRM-0001":       ("SUP-9", "SUP9-PRM-0001-problem-resolution.md"),
}


def rel_path(source_file: Path, target_folder: str, target_file: str) -> str:
    """Relative URL (forward slashes) from source_file's directory to target."""
    target = DOCS_DIR / target_folder / target_file
    return os.path.relpath(target, source_file.parent).replace("\\", "/")


# -----------------------------------------------------------------------
# Phase 1 — Add <a id="…"></a> anchors to definition documents
# -----------------------------------------------------------------------

def add_content_anchors() -> None:
    """
    For each definition document, insert <a id="ID"></a> tags at the first
    appropriate definition site (heading preferred over table row).
    """
    # Group prefixes by the file that defines them
    file_to_prefixes: dict[tuple[str, str], list[str]] = {}
    for prefix, loc in CONTENT_ID_TO_DEF.items():
        file_to_prefixes.setdefault(loc, []).append(prefix)

    for (folder, filename), prefixes in file_to_prefixes.items():
        def_file = DOCS_DIR / folder / filename
        if not def_file.exists():
            print(f"  SKIP (not found): {folder}/{filename}")
            continue

        content = def_file.read_text(encoding="utf-8")

        # Build a pattern matching any content ID with these prefixes
        prefix_pat = "(?:" + "|".join(re.escape(p) for p in prefixes) + r")-\d{3,4}"

        # ---- First pass: record which IDs have dedicated section headings ----
        heading_ids: set[str] = set()
        for line in content.splitlines():
            if re.match(r"^#+\s", line):
                m = re.search(prefix_pat, line)
                if m:
                    heading_ids.add(m.group(0))

        # ---- Second pass: insert anchors ----
        anchored: set[str] = set()
        lines = content.splitlines(keepends=True)
        new_lines: list[str] = []
        in_code_block = False

        for line in lines:
            stripped = line.rstrip("\n\r")

            # Track fenced code blocks — skip them
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                new_lines.append(line)
                continue
            if in_code_block:
                new_lines.append(line)
                continue

            # Skip lines that already carry an anchor tag (idempotent run).
            # Also register the anchored IDs so the following heading won't
            # add a duplicate anchor.
            if '<a id=' in stripped:
                for pre_m in re.finditer(
                    r'<a id="(' + prefix_pat + r')"></a>', stripped
                ):
                    anchored.add(pre_m.group(1))
                new_lines.append(line)
                continue

            # ---- Heading: any # heading line containing an ID ----
            # Use broad re.findall so IDs in parentheses etc. are also caught.
            if re.match(r"^#+\s", stripped):
                ids_in_heading = re.findall(prefix_pat, stripped)
                if ids_in_heading:
                    for full_id in ids_in_heading:
                        if full_id not in anchored:
                            new_lines.append(f'<a id="{full_id}"></a>\n')
                            anchored.add(full_id)
                    new_lines.append(line)
                    continue

            # ---- Table first-cell: | ID | … ----
            table_m = re.match(
                r"^(\|\s*)(" + prefix_pat + r")(\s*\|)",
                stripped,
            )
            if table_m:
                full_id = table_m.group(2)
                # Only anchor here if NO dedicated heading exists for this ID
                if full_id not in anchored and full_id not in heading_ids:
                    anchor_tag = f'<a id="{full_id}"></a>'
                    new_stripped = (
                        stripped[: table_m.start(2)]
                        + anchor_tag
                        + full_id
                        + stripped[table_m.end(2) :]
                    )
                    ending = line[len(stripped) :]
                    new_lines.append(new_stripped + ending)
                    anchored.add(full_id)
                    continue  # already appended modified line

            new_lines.append(line)

        new_content = "".join(new_lines)
        if new_content != content:
            def_file.write_text(new_content, encoding="utf-8")
            print(f"  [anchors] {folder}/{filename}  — {len(anchored)} IDs anchored")
        else:
            print(f"  [anchors] {folder}/{filename}  — no changes (already done?)")


# -----------------------------------------------------------------------
# Phase 2 — Linkify every bare ID in all .md files
# -----------------------------------------------------------------------

# Build combined regex: doc IDs first (they're longer / more specific),
# then content IDs.  Longer alternatives placed first to avoid partial match.
def _build_id_regex() -> re.Pattern[str]:
    doc_ids = sorted(DOC_ID_TO_FILE.keys(), key=len, reverse=True)
    doc_pat = "(?:" + "|".join(re.escape(d) for d in doc_ids) + ")"

    content_prefixes = sorted(CONTENT_ID_TO_DEF.keys(), key=len, reverse=True)
    content_pat = (
        "(?:" + "|".join(re.escape(p) for p in content_prefixes) + r")-\d{3,4}"
    )

    combined = "(?:" + doc_pat + "|" + content_pat + ")"
    return re.compile(combined)


ID_REGEX = _build_id_regex()


def _get_link(full_id: str, source_file: Path) -> str:
    """Return markdown link text [ID](rel-path#ID) or [ID](rel-path)."""
    # Document IDs → link to file (top), no per-document anchor
    if full_id in DOC_ID_TO_FILE:
        folder, filename = DOC_ID_TO_FILE[full_id]
        rp = rel_path(source_file, folder, filename)
        return f"[{full_id}]({rp})"

    # Content IDs → link to file + anchor
    for prefix in sorted(CONTENT_ID_TO_DEF.keys(), key=len, reverse=True):
        if full_id.startswith(prefix + "-"):
            folder, filename = CONTENT_ID_TO_DEF[prefix]
            rp = rel_path(source_file, folder, filename)
            return f"[{full_id}]({rp}#{full_id})"

    return full_id  # fallback (should not happen)


def linkify_file(filepath: Path) -> None:
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    new_lines: list[str] = []
    in_code_block = False
    modified = False

    for line in lines:
        stripped = line.rstrip("\n\r")
        ending = line[len(stripped) :]  # preserve \n / \r\n

        # ---- Track fenced code blocks ----
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        # ---- Mask regions we must NOT linkify ----

        # (a) Inline code spans  `...`
        code_spans: list[str] = []

        def mask_code(m: re.Match) -> str:
            code_spans.append(m.group(0))
            return f"\x00CS{len(code_spans)-1}\x00"

        masked = re.sub(r"`[^`\n]+`", mask_code, stripped)

        # (b) Existing markdown links  [text](url)
        links: list[str] = []

        def mask_link(m: re.Match) -> str:
            links.append(m.group(0))
            return f"\x00LK{len(links)-1}\x00"

        masked = re.sub(r"\[[^\]\n]*\]\([^)\n]*\)", mask_link, masked)

        # (c) HTML anchor tags  <a …>…</a>  (single-line)
        anchors_html: list[str] = []

        def mask_anchor(m: re.Match) -> str:
            anchors_html.append(m.group(0))
            return f"\x00AH{len(anchors_html)-1}\x00"

        masked = re.sub(r"<a\b[^>\n]*>[^<\n]*</a>", mask_anchor, masked)

        # ---- Replace bare IDs with links ----
        def replace_id(m: re.Match) -> str:
            return _get_link(m.group(0), filepath)

        new_masked = ID_REGEX.sub(replace_id, masked)
        changed = new_masked != masked

        # ---- Restore masks ----
        for i, span in enumerate(code_spans):
            new_masked = new_masked.replace(f"\x00CS{i}\x00", span)
        for i, lk in enumerate(links):
            new_masked = new_masked.replace(f"\x00LK{i}\x00", lk)
        for i, ah in enumerate(anchors_html):
            new_masked = new_masked.replace(f"\x00AH{i}\x00", ah)

        new_lines.append(new_masked + ending)
        if changed:
            modified = True

    if modified:
        filepath.write_text("".join(new_lines), encoding="utf-8")
        print(f"  [links]   {filepath.relative_to(DOCS_DIR.parent)}")


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main() -> None:
    print("=== Phase 1: Adding HTML anchors to definition documents ===")
    add_content_anchors()

    print("\n=== Phase 2: Adding markdown links in all .md files ===")
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        linkify_file(md_file)

    print("\nDone!")


if __name__ == "__main__":
    main()
