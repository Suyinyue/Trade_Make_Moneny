# -*- coding: utf-8 -*-
"""检查 docx 结构: XML 合法性 + OOXML 子元素顺序 + 内容概览"""
import sys
import zipfile
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ORDERS = {
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
            "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
            "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
            "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
            "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
            "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
    "rPr": ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
            "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish",
            "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight",
            "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
            "eastAsianLayout", "specVanish", "oMath"],
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
              "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
              "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap",
             "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark", "headers",
             "cellIns", "cellDel", "cellMerge", "tcPrChange"],
    "trPr": ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit",
             "trHeight", "tblHeader", "tblCellSpacing", "jc", "hidden", "ins", "del", "trPrChange"],
}

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    names = z.namelist()
    xml = z.read("word/document.xml")
root = etree.fromstring(xml)
print("document.xml 解析成功;根:", root.tag.split('}')[1])

problems = 0
for tag, order in ORDERS.items():
    for el in root.iter(W + tag):
        idx = [order.index(ch.tag.replace(W, "")) for ch in el
               if ch.tag.replace(W, "") in order]
        unknown = [ch.tag.replace(W, "") for ch in el if ch.tag.replace(W, "") not in order]
        if idx != sorted(idx):
            problems += 1
            names_ = [order[i] for i in idx]
            if problems <= 8:
                print(f"  顺序错误 <{tag}>: {names_}")
        for u in unknown:
            problems += 1
            if problems <= 12:
                print(f"  未知子元素 <{tag}>: <{u}>")
print(f"顺序/未知元素问题数: {problems}")

body = root.find(W + "body")
paras = body.findall(W + "p")
tables = body.findall(W + "tbl")
print(f"正文段落 {len(paras)} 个, 表格 {len(tables)} 个")
for i, t in enumerate(tables):
    rows = t.findall(W + "tr")
    cols = len(rows[0].findall(W + "tc")) if rows else 0
    first = "".join(rows[0].itertext())[:60] if rows else ""
    print(f"  表{i+1}: {len(rows)}行×{cols}列  首行: {first}")

texts = [p for p in root.iter(W + "p")]
all_text = "".join(texts[0].itertext()) if texts else ""
print("\n前 12 段文本:")
n = 0
for p in texts:
    t = "".join(p.itertext()).strip()
    if t:
        print("  -", t[:70])
        n += 1
    if n >= 12:
        break
print("\n各部分:", [x for x in names if x.startswith("word/")][:12])
