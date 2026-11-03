# -*- coding: utf-8 -*-
"""生成 Word 报告与 Excel 数据表"""
import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path("E:/Work/MakeMoney/output")
CHARTS = OUT / "charts"

daily = pd.read_csv(OUT / "600487_daily.csv")
annual = pd.read_csv(OUT / "600487_annual.csv")
events = pd.read_csv(OUT / "600487_events.csv", parse_dates=["d"])
swings = pd.read_csv(OUT / "600487_swings.csv")
stats = json.loads((OUT / "600487_stats.json").read_text(encoding="utf-8"))
extras = json.loads((OUT / "600487_extras.json").read_text(encoding="utf-8"))

INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
MUTED = RGBColor(0x89, 0x87, 0x81)
ACCENT = RGBColor(0x1C, 0x5C, 0xAB)

BODY_FONT = "宋体"
HEAD_FONT = "微软雅黑"
HEADER_BG = "EFEEE9"
ZEBRA_BG = "F7F6F2"
BORDER = "D9D8D2"


# ---------------------------------------------------------------- 基础工具
def set_run_font(run, name=BODY_FONT, size=None, bold=None, color=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def para(doc, text="", size=10.5, bold=False, color=INK, align=None,
         space_before=0, space_after=6, line=1.45, font=BODY_FONT, indent=True):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent and align is None:
        pf.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    if text:
        set_run_font(p.add_run(text), font, size, bold, color)
    return p


def heading(doc, text, level=1):
    sizes = {1: 14, 2: 11.5}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    set_run_font(p.add_run(text), HEAD_FONT, sizes.get(level, 11), True, INK)
    # 一级标题加一条细分隔线
    if level == 1:
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "4")
        bottom.set(qn("w:color"), BORDER)
        pBdr.append(bottom)
        pPr.insert_element_before(pBdr, "w:shd", "w:tabs", "w:spacing", "w:ind",
                                   "w:contextualSpacing", "w:jc", "w:rPr")
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(10)
    set_run_font(p.add_run(text), HEAD_FONT, 8.5, False, MUTED)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def set_cell_margins(table, top=40, bottom=40, left=80, right=80):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for tag, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription")


def set_borders(table, color=BORDER, sz=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblCellMar",
                                "w:tblLook", "w:tblCaption", "w:tblDescription")


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def no_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_table(doc, headers, rows, widths, font_size=8.5, align=None,
              header_bg=HEADER_BG, zebra=True):
    """align: 每列 'l'/'c'/'r'"""
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_borders(table)
    set_cell_margins(table)
    align = align or ["c"] * len(headers)

    hdr = table.rows[0]
    no_split(hdr)
    repeat_header(hdr)
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.width = Cm(widths[i])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        set_run_font(p.add_run(h), HEAD_FONT, font_size, True, INK2)
        shade(cell, header_bg)

    amap = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER, "r": WD_ALIGN_PARAGRAPH.RIGHT}
    for ri, row in enumerate(rows):
        cells = table.add_row()
        no_split(cells)
        for ci, val in enumerate(row):
            cell = cells.cells[ci]
            cell.width = Cm(widths[ci])
            p = cell.paragraphs[0]
            p.alignment = amap[align[ci]]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            set_run_font(p.add_run(str(val)), BODY_FONT, font_size, False, INK)
            if zebra and ri % 2 == 1:
                shade(cell, ZEBRA_BG)
    # 列宽需要逐列设置
    for ci, w in enumerate(widths):
        table.columns[ci].width = Cm(w)
    return table


def pct(v, digits=2, signed=True):
    if pd.isna(v):
        return "—"
    s = f"{v:+.{digits}f}%" if signed else f"{v:.{digits}f}%"
    return s


def num(v, digits=2, thousands=False):
    if pd.isna(v):
        return "—"
    return f"{v:,.{digits}f}" if thousands else f"{v:.{digits}f}"


# ---------------------------------------------------------------- 文档
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = Cm(2.3)
sec.bottom_margin = Cm(2.0)

normal = doc.styles["Normal"]
normal.font.name = BODY_FONT
normal.font.size = Pt(10.5)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

# 页脚页码
footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run_font(footer_p.add_run("亨通光电（600487.SH）上市以来股价全史  ·  "), HEAD_FONT, 8, False, MUTED)
run = footer_p.add_run()
set_run_font(run, HEAD_FONT, 8, False, MUTED)
f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
run._r.append(f1); run._r.append(it); run._r.append(f2)

# ---------- 封面区 ----------
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(30)
p.paragraph_format.space_after = Pt(2)
set_run_font(p.add_run("亨通光电（600487.SH）"), HEAD_FONT, 24, True, INK)
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(4)
set_run_font(p.add_run("上市以来股价全史"), HEAD_FONT, 24, True, INK)
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(14)
set_run_font(p.add_run("2003 年 8 月 22 日 — 2026 年 10 月 30 日 · 5,450 个交易日"), HEAD_FONT, 10.5, False, INK2)

line = doc.add_paragraph()
line.paragraph_format.space_after = Pt(16)
pPr = line._p.get_or_add_pPr()
pBdr = OxmlElement("w:pBdr")
bottom = OxmlElement("w:bottom")
bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "12")
bottom.set(qn("w:space"), "1"); bottom.set(qn("w:color"), "1C5CAB")
pBdr.append(bottom)
pPr.insert_element_before(pBdr, "w:shd", "w:tabs", "w:spacing", "w:ind",
                          "w:contextualSpacing", "w:jc", "w:rPr")

# 摘要
para(doc,
     f'亨通光电于 2003 年 8 月 22 日在上交所上市，首日收盘 13.04 元。截至 2026 年 10 月 30 日，'
     f'股价收于 42.42 元，不复权累计上涨 {stats["不复权累计涨幅(%)"]:.2f}%；'
     f'若按前复权价（把历次分红送转还原为同一口径）计算，累计涨幅为 {stats["前复权累计涨幅(%)"]:,.2f}%，'
     f'折合年化收益 {stats["年化收益率(%)"]:.2f}%——上市首日投入的 1 万元，若持有至今并参与全部分红送转，'
     f'市值约为 {1 + stats["前复权累计涨幅(%)"] / 100:.1f} 万元。'
     f'二十三年间股价经历四轮大级别行情，其间最大回撤达 −{abs(stats["最大回撤(%)"]):.2f}%（2008 年 2 月至 10 月），'
     f'2026 年 6 月创下 {stats["盘中最高价(不复权)"]:.2f} 元的历史最高价后，四个月内回落逾六成。',
     size=10.5, space_after=4)

# ---------- 一、关键数据 ----------
heading(doc, "一、关键数据一览")

kv = [
    ("上市日期", "2003-08-22", "最新交易日", stats["最后交易日"]),
    ("上市首日开盘 / 收盘", "13.30 / 13.04 元", "最新收盘", f'{stats["最新收盘"]:.2f} 元'),
    ("历史最高价（盘中）", f'{stats["盘中最高价(不复权)"]:.2f} 元（{stats["盘中最高价日期"]}）',
     "历史最低价（盘中）", f'{stats["盘中最低价(不复权)"]:.2f} 元（{stats["盘中最低价日期"]}）'),
    ("前复权最高收盘", f'{stats["收盘最高(前复权)"]:.2f} 元（{stats["收盘最高日期"]}）',
     "前复权最低收盘", f'{stats["收盘最低(前复权)"]:.2f} 元（{stats["收盘最低日期"]}）'),
    ("不复权累计涨幅", f'+{stats["不复权累计涨幅(%)"]:,.2f}%',
     "前复权累计涨幅", f'+{stats["前复权累计涨幅(%)"]:,.2f}%'),
    ("年化收益率", f'{stats["年化收益率(%)"]:.2f}%（{stats["持有年数"]} 年）',
     "最大回撤", f'{stats["最大回撤(%)"]:.2f}%'),
    ("最大回撤区间", f'{stats["最大回撤峰值日"]} → {stats["最大回撤谷底日"]}',
     "上涨 / 下跌年份", f'{stats["上涨年份"]} / {stats["下跌年份"]} 年'),
    ("单日最大涨幅", f'+{extras["best_days"][0]["涨跌幅(前复权%)"]:.2f}%（{str(extras["best_days"][0]["日期"])[:10]}）',
     "单日最大跌幅", f'{extras["worst_days"][0]["涨跌幅(前复权%)"]:.2f}%（{str(extras["worst_days"][0]["日期"])[:10]}）'),
    ("除权除息次数", f'{stats["除权除息次数"]} 次', "交易日总数", f'{stats["交易日总数"]:,} 天'),
]
add_table(doc, ["项目", "数值", "项目", "数值"], kv,
          widths=[4.0, 4.3, 4.0, 4.3], font_size=8.5,
          align=["l", "l", "l", "l"])
caption(doc, "表 1　关键数据一览（价格单位：元；涨跌幅口径见文末说明）")

# ---------- 二、股价全景 ----------
heading(doc, "二、股价全景")
para(doc,
     f'下图为上市以来的前复权收盘价（对数坐标）。前复权价把 2003 年以来的 {stats["除权除息次数"]} 次分红送转还原到当前股本口径，'
     "因此纵轴上的价格可以直接比较长期收益；对数坐标则让早期的几毛钱与今天的几十元在同一张图上具有可比性。")
doc.add_picture(str(CHARTS / "chart_price.png"), width=Cm(16.4))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
caption(doc, "图 1　亨通光电上市以来前复权收盘价（对数坐标）")

para(doc,
     "走势大致可以分为几个阶段：2003—2005 年上市初期的估值回归，前复权价一度跌至 0.53 元；"
     "2005 年股权分置改革（流通股东每 10 股获送 4.5 股）复牌后，随 2006—2007 年大牛市一路上行；2008 年金融危机中回撤近八成；"
     "其后在 2009—2010 年、2014—2015 年、2016—2017 年三轮行情中拾级而上；"
     "2018—2024 年长期在 10—30 元区间震荡；2024 年末起再度走强，2026 年 6 月 25 日最高收于 122.70 元。")

# ---------- 三、年度表现 ----------
heading(doc, "三、年度表现")
para(doc,
     "下表按年度汇总。价格列为前复权价，可直接跨年比较；「年末收盘（不复权）」为当年最后一个交易日的实际成交价，"
     "用于对照当时的真实价位。年度涨跌幅按前复权收盘价计算，已包含分红送转的影响。")
rows = []
for _, r in annual.iterrows():
    rows.append([
        int(r["年份"]), int(r["交易日"]), num(r["开盘(前复权)"]), num(r["最高(前复权)"]),
        num(r["最低(前复权)"]), num(r["收盘(前复权)"]), num(r["收盘(不复权)"]),
        pct(r["年度涨跌幅(%)"]), pct(r["年内振幅(%)"], signed=False), num(r["成交量(万手)"], thousands=True),
    ])
add_table(doc, ["年份", "交易日", "开盘", "最高", "最低", "收盘", "年末收盘\n（不复权）",
                "涨跌幅", "振幅", "成交量\n（万手）"],
          rows, widths=[1.2, 1.3, 1.6, 1.6, 1.6, 1.6, 1.95, 1.95, 1.65, 2.05],
          font_size=8, align=["c", "c", "r", "r", "r", "r", "r", "r", "r", "r"])
caption(doc, "表 2　年度表现（2003 年为上市当年 8 月 22 日起；2026 年截至 10 月 30 日）")

doc.add_picture(str(CHARTS / "chart_annual.png"), width=Cm(16.4))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
caption(doc, "图 2　年度涨跌幅（前复权，含分红送转）")

para(doc,
     f'24 个年度中 {stats["上涨年份"]} 年上涨、{stats["下跌年份"]} 年下跌。涨幅最大的三年是 2009 年（+226.13%）、'
     "2015 年（+153.12%）和 2017 年（+117.61%）；跌幅最大的是 2011 年（−59.77%）、2008 年（−54.75%）"
     "和 2018 年（−40.62%）。2026 年至今上涨 71.96%，但年内振幅高达 426.32%，是上市以来波动最剧烈的一年。")

# ---------- 四、历史大波段 ----------
heading(doc, "四、历史大波段")
para(doc,
     "以 40% 的反向幅度识别拐点，上市以来共出现 22 个超过 40% 的单向行情。下表列出全部波段，"
     "可以看出这只股票的长期收益主要由少数几轮大行情贡献，其余时间多在宽幅震荡中度过。")
rows = []
for _, r in swings.iterrows():
    rows.append([r["起点"], num(r["起点价"], 3), r["终点"], num(r["终点价"], 3),
                 pct(r["涨跌幅(%)"]), num(r["历时(月)"], 1)])
add_table(doc, ["起点", "起点价（前复权）", "终点", "终点价（前复权）", "涨跌幅", "历时（月）"],
          rows, widths=[2.9, 3.3, 2.9, 3.3, 2.2, 1.9], font_size=8,
          align=["c", "r", "c", "r", "r", "r"])
caption(doc, "表 3　上市以来 40% 以上大波段（前复权价，单位：元）")

para(doc,
     "最长的两段上涨分别出现在 2008 年 10 月至 2010 年 12 月（+650.19%）与 2005 年 5 月至 2008 年 2 月（+638.61%）；"
     "2024 年 2 月至 2026 年 6 月的一段上涨 +1,084.69%，是上市以来幅度最大的一轮；"
     "而 2026 年 6 月见顶后，股价在四个月内由 122.70 元跌至 42.42 元，回撤 65.4%。")

# ---------- 五、除权除息 ----------
heading(doc, "五、除权除息与复权")
para(doc,
     f'股价的长期比较必须处理分红送转。亨通光电上市以来共发生 {stats["除权除息次数"]} 次除权除息，其中 4 次为大比例送转：'
     "2005 年 8 月股权分置改革（每 10 股送 4.5 股）、2014 年 5 月（10 转 5 派 1.7 元）、"
     "2015 年 9 月（10 转 20）、2018 年 6 月（10 送 4 派 1.6 元），对应复权调整幅度分别为 −31.0%、−33.9%、−66.7% 和 −29.0%。"
     "叠加历次现金分红后，后复权因子从 1.00 累计放大到 11.03。"
     "表中「复权调整」为该次除权除息造成的理论价格下调幅度，数值越小说明送转比例越大。")
rows = []
for _, r in events.iterrows():
    adj = r["相对上次调整(%)"]
    if pd.isna(adj):
        continue
    kind = "大比例送转" if adj <= -10 else "现金分红"
    rows.append([r["d"].strftime("%Y-%m-%d"), pct(adj), kind])
add_table(doc, ["除权除息日", "复权调整", "类型"], rows,
          widths=[4.2, 4.2, 8.0], font_size=8,
          align=["c", "r", "c"])
caption(doc, f'表 4　历次除权除息（共 {stats["除权除息次数"]} 次）')
para(doc,
     f'正因为有这些送转，复权与不复权两条曲线差异极大：以不复权价计，股价从 13.04 元到 42.42 元「只」涨了 225%；'
     f'以前复权价计，累计收益为 {stats["前复权累计涨幅(%)"]:,.0f}%。看长期股价时，不复权价会严重低估真实回报。')

# ---------- 六、区间收益 ----------
heading(doc, "六、区间收益")
rows = [[k, f"{v:+,.2f}%"] for k, v in extras["periods"].items()]
add_table(doc, ["区间", "涨跌幅（前复权）"], rows,
          widths=[9.0, 7.0], font_size=9, align=["l", "r"])
caption(doc, "表 5　不同持有期的累计收益（截至 2026-10-30）")
p1 = extras["periods"]["近 1 年（2025-10-30 起）"]
p3 = extras["periods"]["近 3 年（2023-10-30 起）"]
p5 = extras["periods"]["近 5 年（2021-10-29 起）"]
p10 = extras["periods"]["近 10 年（2016-10-31 起）"]
end2025 = float(daily.loc[daily["日期"] == "2025-12-31", "收盘(前复权)"].iloc[0])
mult2025 = end2025 / float(daily["收盘(前复权)"].iloc[0])
para(doc,
     f'截至最新交易日，近一年上涨 {p1:.2f}%，近三年上涨 {p3:.2f}%，近五年上涨 {p5:.2f}%，近十年上涨 {p10:.2f}%，'
     f'上市以来上涨 {stats["前复权累计涨幅(%)"]:,.2f}%。需要注意的是，长期收益高度集中于 2025—2026 年的行情：'
     f'若只持有到 2025 年末，累计收益约为 {mult2025:.1f} 倍（{(mult2025 - 1) * 100:,.0f}%），'
     f'最后十个月的上涨贡献了其余部分。')

# ---------- 七、说明 ----------
heading(doc, "七、数据说明")
notes = [
    f'数据来源：日线行情（不复权开盘、最高、最低、收盘及成交量）取自腾讯财经行情接口；复权因子取自新浪财经除权除息数据，共 {stats["除权除息次数"]} 次；4 次大比例送转的方案内容经公司公告核对。',
    "复权口径：前复权价 = 不复权价 ÷ 前复权因子，后复权价 = 不复权价 × 后复权因子。前复权价按最新股本折算，适合比较长期收益；不复权价为当时实际成交价。",
    "交易日总数 5,450 天（2003-08-22 至 2026-10-30）。其中 2007-09-04 的行情在原始接口中缺失，由复权数据反推补齐。",
    "年度涨跌幅以上一交易日收盘为基期，按前复权收盘价计算；2003 年、2026 年为不完整年度。",
    "年化收益率按 23.19 年几何平均计算；最大回撤按前复权收盘价的峰谷区间计算，未计交易成本、税费与分红再投资的时间差。",
    "成交量为手（1 手 = 100 股）；原始数据仅提供成交量，未包含成交额。",
    "配套数据文件：亨通光电600487_上市以来股价数据.xlsx，含日线明细（5,450 行）、年度汇总、除权除息与大波段明细。",
    "本文档由公开行情数据整理生成，生成日期 2026 年 11 月 1 日，仅供研究参考，不构成任何投资建议。",
]
for i, t in enumerate(notes, 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.4
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    set_run_font(p.add_run(f"{i}. "), BODY_FONT, 9, True, INK2)
    set_run_font(p.add_run(t), BODY_FONT, 9, False, INK2)

doc.save(OUT / "亨通光电600487_上市以来股价全史.docx")
print("Word 已生成")

# ---------------------------------------------------------------- Excel
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
head_fill = PatternFill("solid", fgColor="EFEEE9")
head_font = Font(name="微软雅黑", size=10, bold=True, color="333333")
body_font = Font(name="等线", size=10)
thin = Side(style="thin", color="D9D8D2")
border = Border(left=thin, right=thin, top=thin, bottom=thin)


def py(v):
    return v.item() if hasattr(v, "item") else v


def style_sheet(ws, widths, n_head=1, wrap_cols=()):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=len(widths)):
        for c in row:
            c.border = border
            c.font = body_font
            if c.row <= n_head:
                c.fill = head_fill
                c.font = head_font
                c.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = f"A{n_head + 1}"
    ws.auto_filter.ref = f"A{n_head}:{get_column_letter(len(widths))}{ws.max_row}"


# 1 概览
ws = wb.active
ws.title = "概览"
ws.append(["亨通光电（600487.SH）上市以来股价数据"])
ws["A1"].font = Font(name="微软雅黑", size=14, bold=True)
ws.append([])
ws.append(["数据区间", f'{stats["首个交易日"]} 至 {stats["最后交易日"]}'])
ws.append(["交易日总数", stats["交易日总数"]])
for k in ["上市首日开盘", "上市首日收盘", "最新收盘", "最新收盘(后复权)",
          "不复权累计涨幅(%)", "前复权累计涨幅(%)", "年化收益率(%)", "持有年数",
          "盘中最高价(不复权)", "盘中最高价日期", "盘中最低价(不复权)", "盘中最低价日期",
          "收盘最高(前复权)", "收盘最高日期", "收盘最低(前复权)", "收盘最低日期",
          "单日最大涨幅(%)", "单日最大涨幅日期", "单日最大跌幅(%)", "单日最大跌幅日期",
          "最大回撤(%)", "最大回撤峰值日", "最大回撤谷底日", "上涨年份", "下跌年份", "除权除息次数"]:
    ws.append([k, stats[k]])
ws.column_dimensions["A"].width = 24
ws.column_dimensions["B"].width = 30
for row in ws.iter_rows(min_row=3, max_col=2):
    row[0].font = body_font
    row[0].fill = head_fill

# 2 年度汇总
ws = wb.create_sheet("年度汇总")
ws.append(list(annual.columns))
for _, r in annual.iterrows():
    ws.append([py(v) for v in r])
style_sheet(ws, [8, 8, 12, 12, 12, 12, 12, 12, 12, 14], n_head=1)

# 3 日线
ws = wb.create_sheet("日线数据")
ws.append(list(daily.columns))
for _, r in daily.iterrows():
    ws.append([py(v) for v in r])
style_sheet(ws, [12, 9, 9, 9, 9, 11, 13, 12, 12, 12, 12, 14, 12], n_head=1)
ws.freeze_panes = "B2"

# 4 除权除息
ws = wb.create_sheet("除权除息")
ws.append(["除权除息日", "前复权因子", "复权调整(%)", "类型"])
for _, r in events.iterrows():
    adj = r["相对上次调整(%)"]
    kind = "大比例送转" if adj <= -10 else "现金分红"
    ws.append([r["d"].strftime("%Y-%m-%d"), round(r["qfq因子"], 8), None if pd.isna(adj) else round(adj, 2), kind])
style_sheet(ws, [14, 16, 14, 16], n_head=1)

# 5 大波段
ws = wb.create_sheet("大波段")
ws.append(list(swings.columns))
for _, r in swings.iterrows():
    ws.append([py(v) for v in r])
style_sheet(ws, [13, 13, 13, 13, 12, 10], n_head=1)

wb.save(OUT / "亨通光电600487_上市以来股价数据.xlsx")
print("Excel 已生成")
