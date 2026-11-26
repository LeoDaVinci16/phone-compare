"""Write the outputs: comparison CSVs, an HTML report (single file) and a Quarto/Markdown report."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from .compare import EMPTY, MISSING, Comparison, best_per_spec, goodness
from .data import INFO, Dataset, parse_formula
from .validate import Issue

# --------------------------------------------------------------------------- CSV


def write_csvs(ds: Dataset, comp: Comparison, out_dir: Path, sep: str = ",") -> list[Path]:
    """comparison.csv (what you read), comparison_ratios.csv / comparison_verdicts.csv (numbers to reuse),
    scores_0_100.csv (heatmap values)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "comparison.csv": comp.frame("text"),
        "comparison_ratios.csv": comp.frame("ratio"),
        "comparison_verdicts.csv": comp.frame("verdict"),
        "scores_0_100.csv": goodness(ds).round(1),
    }
    paths = []
    for name, df in files.items():
        df = df.copy()
        df.insert(0, "Is base", ["yes" if n == comp.base else "" for n in df.index])
        path = out_dir / name
        df.to_csv(path, sep=sep, encoding="utf-8-sig")
        paths.append(path)
    return paths


# --------------------------------------------------------------------------- shared pieces

def _css_class(cell) -> str:
    if cell.status == MISSING:
        return "missing"
    if cell.status == EMPTY or math.isnan(cell.verdict):
        return ""
    return "better" if cell.verdict > 0 else "worse" if cell.verdict < 0 else ""


def _value_text(v) -> str:
    if isinstance(v, float):
        return "" if math.isnan(v) else f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def _phone_facts(ds: Dataset, name: str) -> list[tuple[str, str]]:
    """Key facts for a phone section, plus the details stored in the rank files (e.g. chipset info)."""
    facts = []
    for col in ds.phones.columns:
        v = _value_text(ds.phones.at[name, col])
        if not v:
            continue
        table = ds.ranks.get(col)
        if table is not None and table.has(v) and table.details(v):
            v = f"{v} — {table.details(v)}"
        facts.append((col, v))
    return facts


def _value_columns(ds: Dataset) -> list[str]:
    """Spec values table: every column except long free text (notes), which goes in each phone's section."""
    def long_text(col) -> bool:
        return ds.phones[col].astype(str).str.len().max() > 40
    return [c for c in ds.phones.columns
            if not (c in ds.specs and ds.specs[c].compare == INFO and long_text(c))]


def _display_specs(ds: Dataset, comp: Comparison) -> list[str]:
    """Comparison table columns: compared specs first; long info columns (notes, shop) left out."""
    return [s for s in comp.specs if s in ds.specs and ds.specs[s].compare != INFO]


# --------------------------------------------------------------------------- HTML

def _num(v):
    """float -> JSON-safe number (NaN becomes null)."""
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), 4)


def report_data(ds: Dataset, base: str) -> dict:
    """Everything the interactive HTML needs, with the comparison precomputed for EVERY possible base,
    so the report can switch base in the browser without Python."""
    from .compare import compare as run_compare, quantity, uses_score
    from .data import HIGHER, LOWER, RANKED

    compared = [s for s in ds.columns(HIGHER, LOWER, RANKED)]
    comp = {}
    for b in ds.names:
        c = run_compare(ds, b)
        comp[b] = {n: {s: [c.cells[(n, s)].text, _num(c.cells[(n, s)].verdict), _num(c.cells[(n, s)].ratio),
                           c.cells[(n, s)].status] for s in compared} for n in ds.names}

    charted, quantities = [], {}
    for s in compared:
        q = quantity(ds, s)
        if q.notna().sum() == 0:
            continue
        quantities[s] = {n: _num(q[n]) for n in ds.names}
        spec = ds.specs[s]
        entry = {"name": s, "compare": spec.compare, "ranked": spec.compare == RANKED,
                 "usesScore": uses_score(ds, s), "tiers": []}
        if spec.compare == RANKED and not entry["usesScore"]:
            table = ds.ranks[s].table
            worst = table["rank"].max()
            for r in sorted(table["rank"].dropna().unique()):
                entry["tiers"].append({"tier": float(worst - r + 1),
                                       "label": " / ".join(table.index[table["rank"] == r])})
        charted.append(entry)

    g = goodness(ds)
    return {
        "phones": ds.names, "defaultBase": base, "compared": compared, "comp": comp,
        "charted": charted, "specByName": {e["name"]: e for e in charted} | {
            s: {"name": s, "compare": ds.specs[s].compare} for s in compared if s not in quantities},
        "quantity": quantities,
        "values": {n: {s: _value_text(ds.phones.at[n, s]) for s in ds.phones.columns} for n in ds.names},
        "goodnessSpecs": list(g.columns),
        "goodness": {s: {n: _num(g.at[n, s]) for n in ds.names} for s in g.columns},
        "facts": {n: _phone_facts(ds, n) for n in ds.names},
    }


def render_html(ds: Dataset, base: str, issues: list[Issue], selection: dict | None = None,
                server_mode: bool = False) -> str:
    """The interactive report as a string. `ds` is the FULL dataset: the Phones/Specs tabs switch
    phones and specs on/off in the browser, starting from `selection` (data/selection.json)."""
    env = Environment(loader=PackageLoader("phone_compare", "templates"), autoescape=select_autoescape())
    tpl = env.get_template("report.html.j2")
    data = report_data(ds, base)
    data.update({
        "serverMode": server_mode,
        "selection": selection or {"phones_off": [], "specs_off": []},
        "nameColumn": ds.name_column,
        "columns": list(ds.phones.columns),
        "specTypes": {c: (ds.specs[c].compare if c in ds.specs else "") for c in ds.phones.columns},
        "specNotes": {c: (ds.specs[c].notes if c in ds.specs else "") for c in ds.phones.columns},
        "derived": {c: ", ".join(parse_formula(ds.specs[c].formula)[1]) for c in ds.phones.columns
                    if c in ds.specs and ds.specs[c].derived and c not in ds.file_columns},
        "raw": {n: {c: str(ds.raw.at[n, c]) if ds.raw is not None else "" for c in ds.phones.columns} for n in ds.names},
        "rankValues": {s: list(t.table.sort_values("rank", kind="stable").index) for s, t in ds.ranks.items()},
        "rankFiles": {s: t.path.name for s, t in ds.ranks.items()},
        "issues": [{"level": i.level, "message": i.message, "fix": i.fix} for i in issues],
    })
    return tpl.render(
        base=base, generated=datetime.now().strftime("%Y-%m-%d %H:%M"), data_dir=str(ds.data_dir),
        server_mode=server_mode,
        data_json=json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    )


def write_html(ds: Dataset, comp: Comparison, issues: list[Issue], plots: dict | None, path: Path,
               selection: dict | None = None) -> Path:
    """Write the interactive single-file report (works offline, no server needed to view it)."""
    path.write_text(render_html(ds, comp.base, issues, selection), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- Quarto / Markdown

def _md_table(df: pd.DataFrame) -> str:
    def esc(x) -> str:
        return str(x).replace("|", "\\|").replace("\n", " ")
    head = "| " + " | ".join(esc(c) for c in [df.index.name or ""] + list(df.columns)) + " |"
    def is_num(col) -> bool:
        vals = [str(v) for v in df[col] if str(v) not in ("", "nan")]
        return bool(vals) and all(re.fullmatch(r"[+\-]?[\d.,]+%?", v) for v in vals)
    sep = "|" + "|".join([":---"] + ["---:" if is_num(c) else ":---" for c in df.columns]) + "|"
    body = ["| " + " | ".join([esc(i)] + [esc(v) for v in row]) + " |" for i, row in zip(df.index, df.values)]
    return "\n".join([head, sep, *body])


def _chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def write_markdown(ds: Dataset, comp: Comparison, issues: list[Issue], plots: dict, path: Path,
                   quarto: bool = True) -> Path:
    """report.qmd (render with `quarto render report.qmd --to html` or `--to pdf`) or plain report.md.
    Wide tables are split into groups of 6 specs so they fit on a page."""
    rel = lambda p: Path(p).relative_to(path.parent).as_posix()  # noqa: E731
    marked = lambda n: f"**{n}** (base)" if n == comp.base else n  # noqa: E731
    out: list[str] = []
    title = "Phone comparison"
    if quarto:
        out += ["---", f'title: "{title}"', f'subtitle: "Base: {comp.base}"',
                f'date: "{datetime.now():%Y-%m-%d}"', "format:", "  html:", "    toc: true",
                "    embed-resources: true", "  pdf:", "    toc: true",
                "    geometry: [landscape, margin=1.5cm]", "    fontsize: 9pt", "---", ""]
    else:
        out += [f"# {title}", "", f"Base: **{comp.base}** · generated {datetime.now():%Y-%m-%d %H:%M}", ""]

    out += ["## Summary", ""]
    if issues:
        out.append(f"**{len(issues)} thing(s) to fix in the data:**\n")
        out += [f"- {i.message}  \n  → {i.fix}" for i in issues]
    else:
        out.append("Every spec has a type and every ranked value has a rank.")
    best = best_per_spec(ds)
    if not best.empty:
        out += ["", "### Best phone for each spec", "", _md_table(best.set_index("Spec"))]

    out += ["", "## Comparison vs base", "",
            "% = difference vs the base. Price and weight: lower is better. "
            "Ranked specs without a score show better/worse by rank.", ""]
    text = comp.frame("text")
    text.index = [marked(n) for n in text.index]
    text.index.name = "Phone"
    for group in _chunks(_display_specs(ds, comp), 6):
        out += [_md_table(text[group]), ""]

    out += ["## Spec values", ""]
    vals = ds.phones.map(_value_text)
    vals.index = [marked(n) for n in vals.index]
    vals.index.name = "Phone"
    for group in _chunks([c for c in _value_columns(ds) if c in vals.columns], 6):
        out += [_md_table(vals[group]), ""]

    if plots.get("overview"):
        out += ["## Overview", "", "Each spec scored 0–100 within this list (100 = best).", "",
                f"![Overview]({rel(plots['overview'])})", ""]
    out += ["## Per spec", "", "Every phone sorted from low to high; the base is orange.", ""]
    for name, p in plots.get("specs", {}).items():
        out += [f"![{name}]({rel(p)})", ""]
    out += ["## Per phone", ""]
    for n in comp.phones:
        out += [f"### {n}{' (base)' if n == comp.base else ''}", ""]
        for k, v in _phone_facts(ds, n):
            out.append(f"- **{k}:** {v}")
        if n in plots.get("phones", {}):
            out += ["", f"![{n}]({rel(plots['phones'][n])})"]
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")
    return path

