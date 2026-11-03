# -*- coding: utf-8 -*-
"""把 docx 内容按顺序导出为纯文本, 便于校对"""
import sys
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

doc = Document(sys.argv[1])
body = doc.element.body
out = []
for child in body.iterchildren():
    tag = child.tag.split('}')[1]
    if tag == "p":
        t = Paragraph(child, doc).text.strip()
        if t:
            out.append(t)
    elif tag == "tbl":
        tbl = Table(child, doc)
        out.append(f"[表格 {len(tbl.rows)}×{len(tbl.columns)}]")
        for r in tbl.rows:
            out.append(" | ".join(c.text.replace("\n", "/") for c in r.cells))
        out.append("[/表格]")
from pathlib import Path
Path(sys.argv[2]).write_text("\n".join(out), encoding="utf-8")
