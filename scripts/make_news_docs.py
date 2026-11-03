# -*- coding: utf-8 -*-
"""生成亨通光电近期新闻集合（xlsx / md）与新闻简报（docx）"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from news_data import RECENT, BACKGROUND, EVENTS, FIN, PLACEMENT, MONTHLY

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path("E:/Work/MakeMoney/output")
INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
MUTED = RGBColor(0x89, 0x87, 0x81)
ACCENT = RGBColor(0x1C, 0x5C, 0xAB)
BODY_FONT, HEAD_FONT = "宋体", "微软雅黑"
HEADER_BG, ZEBRA_BG, BORDER = "EFEEE9", "F7F6F2", "D9D8D2"


# ---------------------------------------------------------------- docx 工具
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


def bullet(doc, lead, text, size=10.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(5)
    pf.line_spacing = 1.45
    pf.left_indent = Cm(0.75)
    pf.first_line_indent = Cm(-0.75)
    set_run_font(p.add_run("◆ "), HEAD_FONT, size - 1, True, ACCENT)
    set_run_font(p.add_run(lead), HEAD_FONT, size, True, INK)
    set_run_font(p.add_run(text), BODY_FONT, size, False, INK)
    return p


def heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    set_run_font(p.add_run(text), HEAD_FONT, 14 if level == 1 else 11.5, True, INK)
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


def add_hyperlink(paragraph, url, text, size=8, color="1C5CAB"):
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        rFonts.set(qn(a), HEAD_FONT)
    rPr.append(rFonts)
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    rPr.append(c)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size * 2)))
    rPr.append(sz)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    run.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_table(doc, headers, rows, widths, font_size=8.5, align=None,
              link_col=None, link_texts=None):
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
        shade(cell, HEADER_BG)

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
            if link_col is not None and ci == link_col:
                add_hyperlink(p, val, link_texts[ri], size=font_size)
            else:
                set_run_font(p.add_run(str(val)), BODY_FONT, font_size, False, INK)
            if ri % 2 == 1:
                shade(cell, ZEBRA_BG)
    for ci, w in enumerate(widths):
        table.columns[ci].width = Cm(w)
    return table


# ---------------------------------------------------------------- 简报 docx
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

footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run_font(footer_p.add_run("亨通光电（600487.SH）近期新闻简报  ·  "), HEAD_FONT, 8, False, MUTED)
run = footer_p.add_run()
set_run_font(run, HEAD_FONT, 8, False, MUTED)
f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
run._r.append(f1); run._r.append(it); run._r.append(f2)

# 标题
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(20)
p.paragraph_format.space_after = Pt(2)
set_run_font(p.add_run("亨通光电（600487.SH）"), HEAD_FONT, 23, True, INK)
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(4)
set_run_font(p.add_run("近期新闻简报"), HEAD_FONT, 23, True, INK)
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(12)
set_run_font(p.add_run("2026 年 8 月 26 日 — 11 月 1 日 · 12 条近期动态 + 5 条背景资料 · 整理日期 2026-11-01"),
             HEAD_FONT, 9.5, False, INK2)

line = doc.add_paragraph()
line.paragraph_format.space_after = Pt(10)
pPr = line._p.get_or_add_pPr()
pBdr = OxmlElement("w:pBdr")
bottom = OxmlElement("w:bottom")
bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "12")
bottom.set(qn("w:space"), "1"); bottom.set(qn("w:color"), "1C5CAB")
pBdr.append(bottom)
pPr.insert_element_before(pBdr, "w:shd", "w:tabs", "w:spacing", "w:ind",
                          "w:contextualSpacing", "w:jc", "w:rPr")

# 核心要点
heading(doc, "核心要点")
bullet(doc, "业绩爆发：",
       "三季度单季归母净利 30.44 亿元、同比增长 299.10%，推动前三季度净利至 61.63 亿元（+159.42%）。"
       "公司归因于 AI 与数据中心资本开支带动光通信需求增长、价格上涨。")
bullet(doc, "订单与扩产：",
       "能源互联在手订单超 240 亿元、海洋通信超 60 亿元；8 月中标 18.31 亿元海洋能源项目。"
       "66.36 亿元定增投向光棒、CPO 封装、FAU 与揭阳海缆基地，向上游材料和高价值器件延伸。")
bullet(doc, "资金面分化：",
       "董事长提议回购 1—2 亿元、公司已持回购股份 2260.55 万股（0.92%）；"
       "但游资章建平夫妇三季度退出前十大股东，股东户数由 59.06 万升至 63.66 万，筹码趋于分散。")
bullet(doc, "股价背离：",
       "8 月上涨 41.52%、9 月下跌 18.58%、10 月再跌 22.68%，10 月 30 日收 42.42 元，"
       "较 6 月 25 日高点回落约 65%，市值约 1046 亿元——业绩超预期与股价调整同时发生。")

# 一、事件时间线
heading(doc, "一、近期事件时间线")
rows = [[r["日期"], r["标题"], r["类别"]] for r in RECENT]
add_table(doc, ["日期", "事件", "类别"], rows,
          widths=[2.5, 11.1, 2.6], font_size=8,
          align=["c", "l", "c"])
caption(doc, "表 1　2026 年 8 月 26 日以来与亨通光电相关的主要动态（按时间倒序）")

# 二、业绩
heading(doc, "二、业绩：三季度单季净利接近去年同期的四倍")
rows = [[r[0]] + list(r[1:]) for r in FIN]
add_table(doc, ["指标（亿元）", "2026Q1", "2026Q2", "2026Q3", "2026 前三季"], rows,
          widths=[5.0, 2.9, 2.9, 2.9, 2.9], font_size=8.5,
          align=["l", "r", "r", "r", "r"])
caption(doc, "表 2　2026 年分季度业绩（Q2 数据按半年报与一季报差额推算；前三季数据来自 2026 年三季报）")

para(doc,
     "业绩加速的核心是光通信。半年报显示光通信业务营收同比增长超过 130%、毛利率超过 60%；"
     "到三季度，单季毛利率升至 24.72%，同比提升约 11.8 个百分点。公司在三季报中将其归因于"
     "“光通信市场需求增长、价格上涨”，叠加海上风电项目交付恢复。"
     "前三季度经营活动现金流净额 8.41 亿元，同比增长 70.57%，回款质量同步改善。")
para(doc,
     "业绩披露节奏也解释了 10 月的股价波动：10 月 16 日晚间发布业绩预告（净利 59.70—63.70 亿元），"
     "10 月 19 日股价涨停至 50.25 元；10 月 28 日三季报落地、数据落在预告区间中上部，"
     "但次日股价反而下跌 7.98%，属于典型的“利好兑现”。")

# 三、订单与资本开支
heading(doc, "三、订单与资本开支：向光棒、CPO 与深海延伸")
para(doc,
     "截至三季报披露日，公司在能源互联领域（海底电缆、海洋工程及陆缆）在手订单超过 240 亿元，"
     "海洋通信业务在手订单超过 60 亿元，PEACE 跨洋海缆项目在手订单超过 3 亿美元。"
     "8 月 26 日晚间公告中标 18.31 亿元国内外海洋能源项目，约占 2025 年经审计营业收入的 2.74%。")
para(doc,
     "9 月 24 日推出的 66.36 亿元定增，是公司上市以来规模最大的一次股权融资。募投结构如下：")
rows = [[r[0], r[1], f"{r[2]:.2f}", r[3]] for r in PLACEMENT]
add_table(doc, ["方向", "项目", "金额（亿元）", "主要内容"], rows,
          widths=[2.6, 5.6, 2.4, 5.9], font_size=8,
          align=["c", "l", "r", "l"])
caption(doc, "表 3　66.36 亿元定增募投结构（据定增预案及媒体报道整理）")
para(doc,
     "值得注意的两条支线：一是光棒自供——内蒙古项目规划 800 吨/年光纤预制棒，叠加既有产能扩张，"
     "意在降低对上游材料的依赖；二是 CPO 与 FAU——AI 先进光互联项目规划 FAU 产能约 6300 万片/年，"
     "CPO 先进封装研发投入 1.96 亿元，指向下一代光电封装。定增尚需股东会审议、上交所审核与证监会注册。")
para(doc,
     "此外，分拆子公司亨通华海至科创板上市的事项仍在推进（5 月 29 日董事会通过预案，分拆后仍持股 64.26% 并并表），"
     "市场普遍将其解读为海洋资产的价值重估。")

# 四、股东与资金面
heading(doc, "四、股东与资金面：游资离场，公司与北向接棒")
para(doc,
     "三季报显示，半年报时新进第五大股东的章建平及其妻方文艳已退出前十大股东名单；"
     "同期北向资金（香港中央结算）持股增至 5040.55 万股、占比 2.04%，股东户数由 59.06 万户升至 63.66 万户。"
     "游资筹码离场、散户数量增加、北向增持，三者共同指向筹码结构的重新分配。")
para(doc,
     "11 月 1 日，董事长崔巍提议以 1—2 亿元回购股份，用于员工股权激励或减少注册资本，期限 12 个月。"
     "公司目前已持有回购股份 2260.55 万股（占总股本 0.92%），并拟推出覆盖不超过 222 人、"
     "资金不超过 2.89 亿元的 2026 年员工持股计划。回购提议属于提示性公告，仍需董事会审议。")

# 五、市场表现
heading(doc, "五、市场表现：业绩与股价的背离")
rows = [[r[0], r[1], r[2], r[3]] for r in MONTHLY]
add_table(doc, ["月份", "涨跌幅", "月末收盘（元）", "主要事件"], rows,
          widths=[3.0, 2.4, 3.0, 8.1], font_size=8.5,
          align=["c", "r", "r", "l"])
caption(doc, "表 4　2026 年 8—10 月股价表现（不复权，行情数据）")

rows = [[r[0], r[1], r[2], r[3]] for r in EVENTS]
add_table(doc, ["公告日", "事件", "当日涨跌", "次日涨跌"], rows,
          widths=[2.8, 8.2, 2.6, 2.6], font_size=8.5,
          align=["c", "l", "r", "r"])
caption(doc, "表 5　关键公告与股价反应（公告多在盘后发布，故同时列出次日表现）")

para(doc,
     "把三条线索放在一起看：股价在 6 月 25 日见顶（前复权收盘 122.70 元），此后四个月回撤约 65%；"
     "而同期基本面是加速向上的——半年报净利 +93%，三季报 +159%。这种背离通常来自两方面："
     "一是前期涨幅过大（按前复权收盘价，2026 年内最大涨幅约 397%），估值需要消化；"
     "二是交易层面的筹码切换，游资退出放大了波动。截至 10 月 30 日，年内仍上涨 71.53%，"
     "总市值约 1046 亿元。")

# 六、机构观点
heading(doc, "六、机构观点")
para(doc,
     "华龙证券（10 月 22 日）预计公司 2026—2028 年归母净利 82.96 / 105.63 / 114.81 亿元；"
     "国联民生（10 月 22 日）预计 85.2 / 104.6 / 117.3 亿元。两家均以 AI 驱动光通信量价齐升为核心假设。"
     "需要说明的是，前三季度实际净利 61.63 亿元，意味着机构对四季度的预期隐含较高增长。")
para(doc,
     "谨慎观点同样存在。有媒体评级栏目在 10 月 19 日指出，业绩虽略超预期，但 AI 资本开支的利好"
     "已被较充分定价，建议波段操作；主要风险包括光纤需求不及预期、光棒供给扩张过快、海洋项目交付延后。")

# 七、风险与核查
heading(doc, "七、风险提示与信息核查")
bullet(doc, "审批不确定性：",
       "66.36 亿元定增尚需股东会、上交所与证监会环节；分拆亨通华海至科创板仍需审核注册；"
       "回购仅为董事长提议，须经董事会审议后方可实施。")
bullet(doc, "行业与经营风险：",
       "光纤价格上涨的可持续性、行业扩产带来的供给压力、海上风电项目交付节奏，均可能影响后续业绩。")
bullet(doc, "估值与交易风险：",
       "股价年内振幅超过 400%（前复权最高 124.85 元、最低 23.72 元），短期波动显著高于基本面变化。")
bullet(doc, "未经证实的传闻：",
       "网络流传“1.6T 硅光模块通过英伟达、微软认证并获大额订单”“中金目标价 61.8 元”等说法，"
       "前者来自自媒体、公司未公告，后者为媒体转述、未核对研报原文，本文均未采信为事实。")
para(doc,
     "数据说明：财务数据与公告内容来自公司公告及证券时报、每日经济新闻、上海证券报等公开报道；"
     "行情与涨跌幅为本文档基于日线行情数据自行计算，截至 2026 年 10 月 30 日收盘。"
     "新闻链接见配套文件《亨通光电_近期新闻集合》。本简报仅为公开信息整理，不构成投资建议。",
     size=9, color=INK2, space_before=6)

# 附：新闻索引
heading(doc, "附：近期新闻索引")
rows, links, texts = [], [], []
for r in RECENT:
    rows.append([r["日期"], r["标题"], r["来源"], r["链接"], r["重要度"]])
    links.append(r["链接"])
    texts.append("查看原文")
add_table(doc, ["日期", "标题", "来源", "链接", "重要度"], rows,
          widths=[2.3, 7.0, 3.4, 2.0, 1.5], font_size=7.5,
          align=["c", "l", "l", "c", "c"], link_col=3, link_texts=texts)
caption(doc, "表 6　近期新闻索引（完整条目与摘要见《亨通光电_近期新闻集合.xlsx》）")

rows, texts = [], []
for r in BACKGROUND:
    rows.append([r["日期"], r["标题"], r["来源"], r["链接"], r["重要度"]])
    texts.append("查看原文")
add_table(doc, ["日期", "标题", "来源", "链接", "重要度"], rows,
          widths=[2.3, 7.0, 3.4, 2.0, 1.5], font_size=7.5,
          align=["c", "l", "l", "c", "c"], link_col=3, link_texts=texts)
caption(doc, "表 7　背景资料（2025 年 10 月—2026 年 6 月，用于理解当前业务脉络）")

doc.save(OUT / "亨通光电_近期新闻简报.docx")
print("简报 docx 已生成")

# ---------------------------------------------------------------- Excel
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
head_fill = PatternFill("solid", fgColor="EFEEE9")
head_font = Font(name="微软雅黑", size=10, bold=True, color="333333")
body_font = Font(name="等线", size=10)
link_font = Font(name="等线", size=10, color="1C5CAB", underline="single")
thin = Side(style="thin", color="D9D8D2")
border = Border(left=thin, right=thin, top=thin, bottom=thin)


def sheet(title, headers, rows, widths, link_col=None, wrap_cols=(), freeze="A2"):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=len(widths)):
        for c in row:
            c.border = border
            c.font = body_font
            c.alignment = Alignment(vertical="top", wrap_text=(c.column in wrap_cols),
                                    horizontal="left")
            if c.row == 1:
                c.fill = head_fill
                c.font = head_font
                c.alignment = Alignment(horizontal="center", vertical="center")
    if link_col:
        for i in range(2, ws.max_row + 1):
            cell = ws.cell(row=i, column=link_col)
            if isinstance(cell.value, str) and cell.value.startswith("http"):
                cell.hyperlink = cell.value
                cell.font = link_font
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f"A1:{get_column_letter(len(widths))}{ws.max_row}"
    return ws


def rows_of(items):
    return [[r["日期"], r["类别"], r["标题"], r["来源"], r["链接"], r["摘要"], r["重要度"]]
            for r in items]


col = ["日期", "类别", "标题", "来源", "链接", "摘要", "重要度"]
w = [12, 10, 34, 20, 42, 72, 7]
sheet("近期新闻", col, rows_of(RECENT), w, link_col=5, wrap_cols=(3, 4, 6))
sheet("背景资料", col, rows_of(BACKGROUND), w, link_col=5, wrap_cols=(3, 4, 6))
sheet("事件与股价", ["公告日", "事件", "当日涨跌", "次日涨跌"],
      [list(e) for e in EVENTS], [14, 40, 12, 12])
sheet("财务速览", ["指标（亿元）", "2026Q1", "2026Q2（推算）", "2026Q3", "2026 前三季"],
      [list(f) for f in FIN], [16, 14, 16, 14, 16])
sheet("定增投向", ["方向", "项目", "金额（亿元）", "主要内容"],
      [[p[0], p[1], p[2], p[3]] for p in PLACEMENT], [14, 32, 12, 44])
del wb["Sheet"]
wb.save(OUT / "亨通光电_近期新闻集合.xlsx")
print("新闻集合 xlsx 已生成")

# ---------------------------------------------------------------- Markdown
lines = [
    "# 亨通光电（600487.SH）近期新闻集合",
    "",
    "> 时间范围：2026-08-26 至 2026-11-01；整理日期：2026-11-01。",
    "> 数据来源：公司公告、证券时报、每日经济新闻、上海证券报等公开报道；行情数据为本地日线数据。",
    "",
    "## 一、近期新闻（12 条）",
    "",
]
for i, r in enumerate(RECENT, 1):
    lines += [
        f"### {i}. {r['日期']}　{r['标题']}",
        "",
        f"- **类别**：{r['类别']}　**来源**：{r['来源']}　**重要度**：{r['重要度']}",
        f"- **链接**：{r['链接']}",
        f"- **摘要**：{r['摘要']}",
        "",
    ]
lines += ["## 二、背景资料（5 条）", ""]
for i, r in enumerate(BACKGROUND, 1):
    lines += [
        f"### {i}. {r['日期']}　{r['标题']}",
        "",
        f"- **类别**：{r['类别']}　**来源**：{r['来源']}",
        f"- **链接**：{r['链接']}",
        f"- **摘要**：{r['摘要']}",
        "",
    ]
lines += ["## 三、关键公告与股价反应", "", "| 公告日 | 事件 | 当日涨跌 | 次日涨跌 |", "|---|---|---|---|"]
lines += [f"| {e[0]} | {e[1]} | {e[2]} | {e[3]} |" for e in EVENTS]
lines += ["", "## 四、财务速览（亿元）", "", "| 指标 | 2026Q1 | 2026Q2 | 2026Q3 | 2026 前三季 |", "|---|---|---|---|---|"]
lines += [f"| {f[0]} | {f[1]} | {f[2]} | {f[3]} | {f[4]} |" for f in FIN]
(OUT / "亨通光电_近期新闻集合.md").write_text("\n".join(lines), encoding="utf-8")
print("新闻集合 md 已生成")
