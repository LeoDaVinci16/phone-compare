"""Compare every phone with a base phone, spec by spec (same rules as the spreadsheet).

For each (phone, spec) the result is a :class:`Cell`:

* higher / lower specs  -> % difference vs the base  (``+70%``); if the base is 0
  (e.g. no wireless charging) -> ``better (50 vs 0)`` / ``same``
* ranked spec with a score for both values -> % difference of the scores (chipset: Geekbench 6)
* ranked spec without scores -> better / same / worse by rank (``better (#1 vs #2)``)
* info specs -> the value itself, not compared

``verdict`` is +1 (better than the base), 0 (same) or -1 (worse); it already takes into
account that a lower price or weight is better.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .data import HIGHER, INFO, LOWER, RANKED, Dataset

OK, EMPTY, MISSING = "ok", "empty", "missing"


@dataclass
class Cell:
    text: str                    # what the report shows
    ratio: float = math.nan      # % difference as a fraction (0.7 = +70%); NaN if not a % comparison
    verdict: float = math.nan    # +1 better, 0 same, -1 worse, NaN not compared
    status: str = OK             # ok | empty (no data) | missing (needs a rank or a type)


@dataclass
class Comparison:
    base: str
    cells: dict[tuple[str, str], Cell]   # (phone, spec) -> Cell
    phones: list[str]
    specs: list[str]

    def frame(self, attr: str = "text") -> pd.DataFrame:
        """Table phones × specs of one Cell attribute ('text', 'ratio', 'verdict', 'status')."""
        data = {s: [getattr(self.cells[(n, s)], attr) for n in self.phones] for s in self.specs}
        return pd.DataFrame(data, index=pd.Index(self.phones, name="Phone"))


# --------------------------------------------------------------------------- comparison

def _sign(x: float) -> float:
    return 0.0 if abs(x) < 1e-12 else math.copysign(1.0, x)


def _pct(ratio: float) -> str:
    return f"{ratio:+.0%}" if abs(ratio) >= 0.005 else "0%"


def compare_cell(ds: Dataset, phone: str, base: str, spec_name: str) -> Cell:
    spec = ds.specs.get(spec_name)
    if spec is None:
        return Cell("no type", status=MISSING)
    v = ds.phones.at[phone, spec_name]
    b = ds.phones.at[base, spec_name]

    if spec.compare == INFO:
        return Cell("" if _empty(v) else _fmt(v), status=OK if not _empty(v) else EMPTY)

    if spec.compare in (HIGHER, LOWER):
        if _empty(v) or _empty(b):
            return Cell("", status=EMPTY)
        direction = 1 if spec.compare == HIGHER else -1
        if b == 0:   # no % of zero (e.g. base has no wireless charging): say better/same/worse instead
            verdict = _sign(v) * direction
            word = "same" if verdict == 0 else "better" if verdict > 0 else "worse"
            return Cell(word if verdict == 0 else f"{word} ({_fmt(v)} vs 0)", verdict=verdict)
        ratio = v / b - 1
        return Cell(_pct(ratio), ratio=ratio, verdict=_sign(ratio) * direction)

    if spec.compare == RANKED:
        table = ds.ranks.get(spec_name)
        if _empty(v):
            return Cell("", status=EMPTY)
        if table is None or not table.has(v):
            return Cell(f"no rank: {v}", status=MISSING)
        if _empty(b):
            return Cell("", status=EMPTY)
        if not table.has(b):
            return Cell("base not ranked", status=MISSING)
        sv, sb = table.score(v), table.score(b)
        if not math.isnan(sv) and not math.isnan(sb) and sb != 0:
            ratio = sv / sb - 1
            return Cell(_pct(ratio), ratio=ratio, verdict=_sign(ratio))
        rv, rb = table.rank(v), table.rank(b)
        if rv == rb:
            return Cell("same", verdict=0.0)
        word = "better" if rv < rb else "worse"
        return Cell(f"{word} (#{rv:g} vs #{rb:g})", verdict=1.0 if rv < rb else -1.0)

    return Cell(f"unknown type '{spec.compare}'", status=MISSING)


def compare(ds: Dataset, base: str) -> Comparison:
    if base not in ds.phones.index:
        raise KeyError(f"Base phone '{base}' is not in phones.csv. Options: {', '.join(ds.names)}")
    specs = [c for c in ds.phones.columns]
    cells = {(n, s): compare_cell(ds, n, base, s) for n in ds.names for s in specs}
    return Comparison(base=base, cells=cells, phones=ds.names, specs=specs)


# --------------------------------------------------------------------------- ordering & scores

def quantity(ds: Dataset, spec_name: str) -> pd.Series:
    """The number each phone is sorted by for one spec, so that "more" always means "more of it":

    * numeric specs: the value itself (price ascending = cheap → expensive)
    * ranked specs: the score if every ranked value has one, otherwise the tier
      (worst rank in the file = tier 1, best = highest tier)
    """
    spec = ds.specs[spec_name]
    col = ds.phones[spec_name]
    if spec.is_numeric:
        return col.astype(float)
    if spec.compare != RANKED or spec_name not in ds.ranks:
        return pd.Series(math.nan, index=col.index)
    table = ds.ranks[spec_name]
    known = [v for v in col if v and table.has(v)]
    use_score = bool(known) and all(not math.isnan(table.score(v)) for v in known)
    worst = table.table["rank"].max()

    def q(v):
        if not v or not table.has(v):
            return math.nan
        return table.score(v) if use_score else worst - table.rank(v) + 1

    return col.map(q).astype(float)


def uses_score(ds: Dataset, spec_name: str) -> bool:
    table = ds.ranks.get(spec_name)
    if table is None:
        return False
    known = [v for v in ds.phones[spec_name] if v and table.has(v)]
    return bool(known) and all(not math.isnan(table.score(v)) for v in known)


def goodness(ds: Dataset) -> pd.DataFrame:
    """0–100 per comparable spec: 100 = best phone in the list for that spec, 0 = worst.

    Used for the heatmap, the radar charts and the "best in each spec" summary.
    """
    out = {}
    for spec_name in ds.columns(HIGHER, LOWER, RANKED):
        q = quantity(ds, spec_name)
        if q.notna().sum() == 0:
            continue
        lo, hi = q.min(), q.max()
        g = pd.Series(100.0, index=q.index) if hi == lo else (q - lo) / (hi - lo) * 100
        if ds.specs[spec_name].compare == LOWER:
            g = 100 - g
        out[spec_name] = g.where(q.notna())
    return pd.DataFrame(out, index=pd.Index(ds.names, name="Phone"))


def best_per_spec(ds: Dataset) -> pd.DataFrame:
    """For each comparable spec: the best phone(s) and their value."""
    g = goodness(ds)
    rows = []
    for spec_name in g.columns:
        col = g[spec_name].dropna()
        if col.empty:
            continue
        winners = list(col[col == col.max()].index)
        losers = [n for n in col.index if n not in winners]
        if not losers:
            best = "All (tie)"
        elif len(winners) > 3:
            best = "All except " + ", ".join(losers)
        else:
            best = ", ".join(winners)
        value = ds.phones.at[winners[0], spec_name]
        rows.append({"Spec": spec_name, "Best": best, "Value": _fmt(value)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- small helpers

def _empty(v) -> bool:
    return v is None or v == "" or (isinstance(v, float) and math.isnan(v))


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:g}" if not math.isnan(v) else ""
    return str(v)
