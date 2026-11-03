# -*- coding: utf-8 -*-
"""生成文档用图: 股价全景(对数)、年度涨跌幅"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = Path("E:/Work/MakeMoney/output")
CHARTS = OUT / "charts"
CHARTS.mkdir(exist_ok=True)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
UP = "#e34948"     # A股习惯: 红涨
DOWN = "#008300"   # 绿跌

d = pd.read_csv(OUT / "600487_daily.csv", parse_dates=["日期"])
a = pd.read_csv(OUT / "600487_annual.csv")
d = d.sort_values("日期")


def rounded_bar(ax, x0, w, y, color, ry=4.0, rx_frac=0.28):
    """从0基线到 y 的柱子, 数据端 4px 圆角, 基线端为直角"""
    if y == 0:
        return
    rx = w * rx_frac
    ry = min(abs(y) * 0.25, ry)
    s = 1 if y > 0 else -1
    y0, y1 = 0, y
    r = ry * s
    k = 0.5523
    verts = [
        (x0, y0), (x0, y1 - r),
        (x0, y1 - r + k * r), (x0 + rx - k * rx, y1), (x0 + rx, y1),
        (x0 + w - rx, y1),
        (x0 + w - rx + k * rx, y1), (x0 + w, y1 - r + k * r), (x0 + w, y1 - r),
        (x0 + w, y0), (x0, y0),
    ]
    codes = [MPath.MOVETO, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4,
             MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4,
             MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", zorder=3))


def style_axes(ax):
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)


# ---------------- 图1 股价全景 ----------------
fig, ax = plt.subplots(figsize=(9.6, 4.1), dpi=220)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ax.plot(d["日期"], d["收盘(前复权)"], color=BLUE, lw=1.3,
        solid_joinstyle="round", solid_capstyle="round", zorder=3)

ax.set_yscale("log")
ax.set_ylim(0.45, 180)
ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100])
ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
ax.set_xlim(pd.Timestamp("2003-06-01"), pd.Timestamp("2029-01-01"))
ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2004, 2027, 2)]))
ax.set_xticklabels([str(y) for y in range(2004, 2027, 2)])

last = d.iloc[-1]
ax.scatter([last["日期"]], [last["收盘(前复权)"]], s=46, color=BLUE,
           edgecolor=SURFACE, linewidth=2, zorder=5)
ax.annotate(f"2026-10-30\n42.42 元", xy=(last["日期"], last["收盘(前复权)"]),
            xytext=(12, -4), textcoords="offset points", fontsize=8.5,
            color=INK2, va="center", ha="left")

peak = d.loc[d["收盘(前复权)"].idxmax()]
ax.scatter([peak["日期"]], [peak["收盘(前复权)"]], s=34, color=INK2,
           edgecolor=SURFACE, linewidth=2, zorder=5)
ax.annotate("2026-06-25 122.70 元\n（前复权历史最高）",
            xy=(peak["日期"], peak["收盘(前复权)"]), xytext=(-14, 10),
            textcoords="offset points", fontsize=8.5, color=INK2,
            ha="right", va="bottom")

low = d.loc[d["收盘(前复权)"].idxmin()]
ax.annotate("2005-05-09 0.53 元（前复权历史最低）",
            xy=(low["日期"], low["收盘(前复权)"]), xytext=(pd.Timestamp("2009-06-01"), 0.58),
            fontsize=8.5, color=INK2, ha="left", va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8,
                            shrinkA=2, shrinkB=4))

style_axes(ax)
ax.set_ylabel("收盘价（元，对数坐标）", fontsize=9, color=INK2, labelpad=8)
fig.text(0.012, 0.965, "亨通光电（600487.SH）上市以来股价全景", fontsize=14.5,
         color=INK, weight="bold", va="top")
fig.text(0.012, 0.895, "前复权收盘价，2003-08-22 至 2026-10-30，共 5,450 个交易日",
         fontsize=9.5, color=MUTED, va="top")
fig.subplots_adjust(left=0.068, right=0.985, top=0.86, bottom=0.11)
fig.savefig(CHARTS / "chart_price.png", facecolor=SURFACE)
plt.close(fig)

# ---------------- 图2 年度涨跌幅 ----------------
fig, ax = plt.subplots(figsize=(9.6, 3.5), dpi=220)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

w = 0.62
for i, row in a.iterrows():
    v = row["年度涨跌幅(%)"]
    rounded_bar(ax, row["年份"] - w / 2, w, v, UP if v >= 0 else DOWN, ry=3.2)

ax.axhline(0, color=AXIS, lw=0.9, zorder=4)
ax.set_xlim(2002.2, 2027.6)
ax.set_ylim(-100, 265)
ax.set_yticks([-60, 0, 60, 120, 180, 240])
ax.set_xticks(a["年份"])
ax.set_xticklabels([f"{y}" for y in a["年份"]], rotation=0, fontsize=7.6)

# 只标注最值
idx = a["年度涨跌幅(%)"].idxmax()
row = a.loc[idx]
ax.annotate(f"+{row['年度涨跌幅(%)']:.0f}%", xy=(row["年份"], row["年度涨跌幅(%)"]),
            xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8, color=INK)
idx = a["年度涨跌幅(%)"].idxmin()
row = a.loc[idx]
ax.annotate(f"{row['年度涨跌幅(%)']:.0f}%", xy=(row["年份"], row["年度涨跌幅(%)"]),
            xytext=(0, -14), textcoords="offset points", ha="center", fontsize=8, color=INK)

style_axes(ax)
ax.set_ylabel("涨跌幅（%）", fontsize=9, color=INK2, labelpad=8)
fig.text(0.012, 0.955, "年度涨跌幅（前复权，含分红送转）", fontsize=12.5, color=INK,
         weight="bold", va="top")
fig.text(0.012, 0.878, "红涨绿跌；2003 年为上市当年（8 月 22 日起）、2026 年为截至 10 月 30 日的年内表现",
         fontsize=8.4, color=MUTED, va="top")
fig.subplots_adjust(left=0.062, right=0.99, top=0.80, bottom=0.13)
fig.savefig(CHARTS / "chart_annual.png", facecolor=SURFACE)
plt.close(fig)

print("图表已生成:", CHARTS / "chart_price.png", CHARTS / "chart_annual.png")
