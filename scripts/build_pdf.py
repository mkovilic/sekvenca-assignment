"""docs/guide.md -> docs/guide.pdf (A4) via PyMuPDF's HTML Story."""

from pathlib import Path

import pymupdf as fitz
import markdown

ROOT = Path(__file__).resolve().parents[1]
CSS = """
body { font-family: sans-serif; font-size: 8.6pt; line-height: 1.32; color: #20201e; }
h1 { font-size: 15pt; color: #20201e; margin: 0 0 4pt 0; }
h2 { font-size: 10.5pt; color: #d9561a; margin: 8pt 0 2pt 0; }
p, li { margin: 0 0 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 2pt 0 4pt 0; }
th, td { border: 0.5pt solid #bbb; padding: 2pt 3pt; font-size: 7.8pt; vertical-align: top; }
th { background: #f3ece2; }
code { font-family: monospace; font-size: 7.8pt; }
"""


def main() -> None:
    md = (ROOT / "docs" / "guide.md").read_text(encoding="utf-8")
    html = markdown.markdown(md, extensions=["tables"])
    story = fitz.Story(html=html, user_css=CSS)
    out = ROOT / "docs" / "guide.pdf"
    writer = fitz.DocumentWriter(str(out))
    rect = fitz.paper_rect("a4")
    where = rect + (40, 40, -40, -40)
    more = True
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    print(f"{out} ({fitz.open(out).page_count} pages)")


if __name__ == "__main__":
    main()
