import fitz  # PyMuPDF
import os

# 페이지 상단/하단 몇 %를 header/footer 영역으로 간주할지
HEADER_RATIO = 0.08
FOOTER_RATIO = 0.08


def is_in_header_or_footer(rect, page_height):
    """이미지 rect 가 header 또는 footer 영역 안에 완전히 포함되면 True."""
    header_limit = page_height * HEADER_RATIO
    footer_start = page_height * (1 - FOOTER_RATIO)
    return rect.y1 <= header_limit or rect.y0 >= footer_start


def clean_cell(cell):
    if cell is None:
        return ""
    return str(cell).replace("\n", " ").replace("|", "\\|").strip()


def rows_to_markdown_table(rows, header_row=None):
    """
    추출된 테이블 rows → 마크다운 테이블 문자열.
    header_row 가 주어지면 해당 행을 헤더로 사용(페이지 연속 테이블 처리).
    """
    if not rows:
        return ""

    clean = clean_cell

    if header_row is not None:
        header = [clean(c) for c in header_row]
        data_rows = [[clean(c) for c in row] for row in rows]
    else:
        header = [clean(c) for c in rows[0]]
        data_rows = [[clean(c) for c in row] for row in rows[1:]]

    ncols = len(header)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * ncols) + " |",
    ]
    for row in data_rows:
        padded = (row + [""] * ncols)[:ncols]
        lines.append("| " + " | ".join(padded) + " |")

    return "\n".join(lines)


def pdf_to_markdown(pdf_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    img_dir = os.path.join(output_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    md_filename = os.path.join(output_dir, "output.md")

    with open(md_filename, "w", encoding="utf-8") as md_file:
        prev_table_headers = None  # 이전 페이지 마지막 테이블의 헤더 행
        prev_table_cut_off = False  # 이전 페이지 마지막 테이블이 하단에서 잘렸는지

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_height = page.rect.height
            content_top = page_height * HEADER_RATIO
            content_bottom = page_height * (1 - FOOTER_RATIO)

            md_file.write(f"## Page {page_index + 1}\n\n")

            # ── 테이블 감지 (PyMuPDF 1.23+) ──────────────────────────────
            tables = []
            try:
                tab_finder = page.find_tables()
                tables = tab_finder.tables if tab_finder else []
            except AttributeError:
                pass  # 이전 버전 PyMuPDF: 테이블 감지 미지원

            # 각 테이블 → 마크다운 변환 (연속 테이블에는 헤더 주입)
            table_md_map = {}
            current_last_headers = None
            current_last_cut_off = False

            for t_idx, table in enumerate(tables):
                rows = table.extract()
                if not rows:
                    continue

                inject_header = None
                top_y = table.bbox[1]
                bottom_y = table.bbox[3]

                # 첫 번째 테이블이 페이지 상단 근처에서 시작하고
                # 이전 페이지 테이블이 하단에서 잘렸다면 → 헤더 주입
                # 단, PDF가 이미 첫 행에 동일한 헤더를 반복하고 있으면 주입 불필요
                if (
                    t_idx == 0
                    and prev_table_cut_off
                    and prev_table_headers is not None
                    and top_y <= content_top + page_height * 0.07
                ):
                    first_row_cleaned = [clean_cell(c) for c in rows[0]]
                    prev_headers_cleaned = [clean_cell(c) for c in prev_table_headers]
                    already_has_header = first_row_cleaned == prev_headers_cleaned
                    if not already_has_header:
                        inject_header = prev_table_headers

                table_md_map[id(table)] = rows_to_markdown_table(
                    rows, header_row=inject_header
                )

                # 다음 페이지를 위해 마지막 테이블 상태 추적
                current_last_headers = (
                    prev_table_headers if inject_header is not None else rows[0]
                )
                current_last_cut_off = bottom_y >= content_bottom - page_height * 0.07

            prev_table_headers = current_last_headers
            prev_table_cut_off = current_last_cut_off

            # ── 텍스트 + 테이블을 읽기 순서대로 출력 ────────────────────
            if tables:
                table_bboxes = {id(t): fitz.Rect(t.bbox) for t in tables}
                tables_written = set()
                output_parts = []

                text_dict = page.get_text("dict")
                blocks = sorted(
                    text_dict.get("blocks", []),
                    key=lambda b: (b["bbox"][1], b["bbox"][0]),
                )

                for block in blocks:
                    block_rect = fitz.Rect(block["bbox"])

                    matched_table = None
                    for t in tables:
                        if table_bboxes[id(t)].intersects(block_rect):
                            matched_table = t
                            break

                    if matched_table is not None:
                        tid = id(matched_table)
                        if tid not in tables_written:
                            tables_written.add(tid)
                            if tid in table_md_map:
                                output_parts.append(table_md_map[tid])
                    elif block.get("type") == 0:  # 텍스트 블록
                        lines_text = [
                            "".join(
                                span.get("text", "") for span in line.get("spans", [])
                            )
                            for line in block.get("lines", [])
                        ]
                        block_text = "\n".join(lines_text).strip()
                        if block_text:
                            output_parts.append(block_text)

                # 아직 출력 안 된 테이블 처리
                for t in tables:
                    if id(t) not in tables_written and id(t) in table_md_map:
                        output_parts.append(table_md_map[id(t)])

                md_file.write("\n\n".join(output_parts) + "\n\n")
            else:
                md_file.write(page.get_text() + "\n\n")

            # ── 이미지 추출 (header/footer 영역 이미지 제외) ─────────────
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]

                try:
                    rects = page.get_image_rects(xref)
                    if rects and is_in_header_or_footer(rects[0], page_height):
                        continue
                except Exception:
                    pass  # 위치를 알 수 없는 경우 포함

                base_image = doc.extract_image(xref)
                img_name = f"page{page_index+1}_img{img_index+1}.{base_image['ext']}"
                img_path = os.path.join(img_dir, img_name)

                with open(img_path, "wb") as f:
                    f.write(base_image["image"])

                md_file.write(f"![Image](./images/{img_name})\n\n")

            md_file.write("---\n\n")

    doc.close()
    print(f"변환 완료: {md_filename}")


if __name__ == "__main__":
    pdf_to_markdown(r"C:\Users\sjw19\Downloads\Automotive_SPICE_PAM_31_KR.pdf", "output")
