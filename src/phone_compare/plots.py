"""Charts: one per spec (all phones sorted low → high), one per phone (vs the base), and an overview heatmap."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no window needed: we only save files
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .compare import Comparison, goodness, quantity, uses_score  # noqa: E402
from .data import HIGHER, LOWER, RANKED, Dataset, slugify  # noqa: E402

BASE_COLOR = "#E07B39"
OTHER_COLOR = "#4C72B0"
BETTER = "#2E8B57"
WORSE = "#C0392B"
NEUTRAL = "#8A8A8A"

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
})


def _wrap(name: str, width: int = 18) -> str:
    return "\n".join(textwrap.wrap(name, width)) or name


def _value_label(v) -> str:
    if isinstance(v, float):
        return f"{v:,.0f}" if abs(v) >= 100 else f"{v:g}"
    return str(v)


# --------------------------------------------------------------------------- per spec

def plot_spec(ds: Dataset, spec_name: str, base: str, path: Path) -> Path | None:
    """All phones for one spec, sorted from low to high (price: cheap → expensive; chipset: slow → fast)."""
    spec = ds.specs[spec_name]
    q = quantity(ds, spec_name).dropna().sort_values(kind="stable")
    if q.empty:
        return None
    missing = [n for n in ds.names if n not in q.index]
    names = list(q.index)
    colors = [BASE_COLOR if n == base else OTHER_COLOR for n in names]
    x = np.arange(len(names))

    fig, ax = plt.subplots(figsize=(max(6.5, 0.95 * len(names) + 2), 4.2))
    hint = "lower is better" if spec.compare == LOWER else "higher is better"

    if spec.is_numeric:
        ax.plot(x, q.values, color=OTHER_COLOR, lw=1.5, alpha=0.6, zorder=1)
        ax.scatter(x, q.values, c=colors, s=[90 if n == base else 50 for n in names], zorder=2)
        for xi, v in zip(x, q.values):
            ax.annotate(_value_label(v), (xi, v), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8)
        ax.set_ylabel(spec_name)
        pad = (q.max() - q.min()) * 0.15 or abs(q.max()) * 0.1 or 1
        ax.set_ylim(q.min() - pad, q.max() + pad * 1.6)
    else:  # ranked
        bars = ax.bar(x, q.values, color=colors, width=0.65)
        values = [ds.phones.at[n, spec_name] for n in names]
        for bar, v in zip(bars, values):
            ax.annotate(_wrap(str(v), 16), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 3), ha="center", va="bottom", fontsize=7.5)
        table = ds.ranks[spec_name]
        if uses_score(ds, spec_name):
            ax.set_ylabel("Score")
            hint = "higher score is better"
        else:
            worst = table.table["rank"].max()
            tiers = sorted(set(q.values))
            labels = []
            for t in tiers:
                vals = table.table.index[table.table["rank"] == worst - t + 1]
                labels.append(" / ".join(vals))
            ax.set_yticks(tiers, labels)
            ax.set_ylabel("Tier (rank file)")
            hint = "taller = better rank"
        ax.set_ylim(0, q.max() * 1.25)

    ax.set_xticks(x, [_wrap(n) for n in names], fontsize=7.5)
    ax.set_title(f"{spec_name}  ·  sorted low → high  ({hint})", loc="left")
    ax.grid(axis="y", alpha=0.25)
    for lbl, n in zip(ax.get_xticklabels(), names):
        if n == base:
            lbl.set_color(BASE_COLOR)
            lbl.set_fontweight("bold")
    note = f"Orange = base ({base})."
    if missing:
        note += f"  No data: {', '.join(missing)}."
    fig.text(0.01, 0.01, note, fontsize=7, color=NEUTRAL)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- per phone

def plot_phone(ds: Dataset, comp: Comparison, g: pd.DataFrame, phone: str, path: Path) -> Path:
    """Left: how much better/worse than the base, spec by spec. Right: radar of 0–100 scores vs the base."""
    base = comp.base
    rows = []
    for spec_name in ds.columns():
        spec = ds.specs[spec_name]
        if spec.compare not in (HIGHER, LOWER, RANKED):
            continue
        cell = comp.cells[(phone, spec_name)]
        if math.isnan(cell.verdict):
            continue
        if not math.isnan(cell.ratio):
            adv = cell.ratio * (-1 if spec.compare == LOWER else 1)   # lower price/weight = advantage
            label = cell.text
        else:
            adv, label = 0.0, cell.text
        rows.append((spec_name, adv, cell.verdict, label))

    fig = plt.figure(figsize=(12, max(4.2, 0.36 * len(rows) + 1.5)))
    ax = fig.add_subplot(1, 2, 1)
    if rows:
        names = [r[0] for r in rows][::-1]
        adv = np.array([r[1] for r in rows][::-1])
        verdicts = [r[2] for r in rows][::-1]
        labels = [r[3] for r in rows][::-1]
        shown = np.clip(adv * 100, -150, 150)
        colors = [BETTER if v > 0 else WORSE if v < 0 else NEUTRAL for v in verdicts]
        y = np.arange(len(names))
        ax.barh(y, shown, color=colors, height=0.6)
        for yi, s, lab, col in zip(y, shown, labels, colors):
            if s <= -150:   # clipped on the left: write inside the bar so it doesn't cover the spec name
                ax.text(-147, yi, lab, va="center", ha="left", fontsize=7.5, color="white", fontweight="bold")
                continue
            ax.text(s + (3 if s >= 0 else -3), yi, lab, va="center", ha="left" if s >= 0 else "right",
                    fontsize=7.5, color=col)
        ax.set_yticks(y, names)
        ax.axvline(0, color="#333", lw=0.8)
        lim = max(40, min(150, np.abs(shown).max() * 1.6 + 10))
        ax.set_xlim(-lim, lim)
        ax.set_xlabel("Advantage vs base (%)   ← worse  |  better →")
    ax.set_title("vs base, spec by spec", loc="left")
    ax.grid(axis="x", alpha=0.25)

    # radar
    common = [c for c in g.columns if not math.isnan(g.at[phone, c]) and not math.isnan(g.at[base, c])]
    axr = fig.add_subplot(1, 2, 2, projection="polar")
    if len(common) >= 3:
        ang = np.linspace(0, 2 * np.pi, len(common), endpoint=False).tolist()
        ang += ang[:1]
        for name, color, lw, alpha in ((base, BASE_COLOR, 1.5, 0.10), (phone, OTHER_COLOR, 2.0, 0.20)):
            vals = [g.at[name, c] for c in common]
            vals += vals[:1]
            axr.plot(ang, vals, color=color, lw=lw)
            axr.fill(ang, vals, color=color, alpha=alpha)
        axr.set_xticks(ang[:-1], [_wrap(c, 14) for c in common], fontsize=7)
        axr.set_ylim(0, 100)
        axr.set_yticks([25, 50, 75, 100], ["25", "50", "75", "100"], fontsize=6, color=NEUTRAL)
        handles = [plt.Line2D([], [], color=OTHER_COLOR, lw=2, label=_wrap(phone, 40))]
        if phone != base:
            handles.append(plt.Line2D([], [], color=BASE_COLOR, lw=1.5, label=f"Base: {_wrap(base, 34)}"))
        axr.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=7.5, frameon=False)
    axr.set_title("0–100 score vs the other phones\n(100 = best in the list)", fontsize=9, pad=18)

    fig.suptitle(phone + ("   (base)" if phone == base else ""), fontweight="bold", x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- overview

def plot_heatmap(ds: Dataset, g: pd.DataFrame, base: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(max(8, 0.75 * g.shape[1] + 4), 0.5 * g.shape[0] + 2.2))
    data = g.to_numpy(dtype=float)
    masked = np.ma.masked_invalid(data)
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#EEEEEE")
    im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if not math.isnan(data[i, j]):
                ax.text(j, i, f"{data[i, j]:.0f}", ha="center", va="center", fontsize=7.5)
    ax.set_xticks(range(g.shape[1]), [_wrap(c, 12) for c in g.columns], fontsize=7.5)
    ax.set_yticks(range(g.shape[0]), g.index, fontsize=8)
    for lbl in ax.get_yticklabels():
        if lbl.get_text() == base:
            lbl.set_color(BASE_COLOR)
            lbl.set_fontweight("bold")
    ax.xaxis.tick_top()
    ax.spines[:].set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("0 = worst in list · 100 = best", fontsize=7.5)
    ax.set_title("Overview: every phone × every spec (grey = no data)", loc="left", pad=40)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- all at once

def make_all(ds: Dataset, comp: Comparison, out_dir: Path) -> dict:
    """Write every chart into out_dir/plots and return their paths grouped by kind."""
    plot_dir = out_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    g = goodness(ds)
    result = {"overview": None, "specs": {}, "phones": {}}
    if not g.empty:
        result["overview"] = plot_heatmap(ds, g, comp.base, plot_dir / "overview_heatmap.png")
    for spec_name in ds.columns(HIGHER, LOWER, RANKED):
        p = plot_spec(ds, spec_name, comp.base, plot_dir / f"spec_{slugify(spec_name)}.png")
        if p:
            result["specs"][spec_name] = p
    used: set[str] = set()
    for name in ds.names:
        slug, n = slugify(name), 2
        while slug in used:                  # two names that slugify the same must not overwrite each other
            slug, n = f"{slugify(name)}_{n}", n + 1
        used.add(slug)
        result["phones"][name] = plot_phone(ds, comp, g, name, plot_dir / f"phone_{slug}.png")
    return result
