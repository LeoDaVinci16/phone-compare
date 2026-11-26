"""Find everything that stops a fair comparison and say how to fix it.

These are the same alerts as the spreadsheet: a spec without a type, a ranked value
that is not in its rank file, a missing rank file, numbers that are not numbers...
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data import COMPARE_TYPES, RANKED, Dataset, FormulaError, parse_formula, slugify

ERROR = "error"      # the comparison for that cell/spec can't be made
WARNING = "warning"  # the comparison works, but something looks wrong


@dataclass
class Issue:
    level: str
    message: str
    fix: str

    def __str__(self) -> str:
        icon = "⚠" if self.level == ERROR else "•"
        return f"{icon} {self.message}\n    → {self.fix}"


def find_issues(ds: Dataset) -> list[Issue]:
    issues: list[Issue] = []

    dupes = ds.phones.index[ds.phones.index.duplicated()].unique()
    for name in dupes:
        issues.append(Issue(ERROR, f"Phone '{name}' appears more than once in phones.csv.",
                            "Give each phone a unique name (add the model code)."))

    for col in ds.phones.columns:
        if col not in ds.specs:
            issues.append(Issue(ERROR, f"Column '{col}' in phones.csv has no type.",
                                f"Add a row to specs.csv: {col},higher|lower|ranked|info"))

    for spec in ds.specs.values():
        if spec.derived:
            try:
                _, args = parse_formula(spec.formula)
            except FormulaError as e:
                issues.append(Issue(ERROR, f"Spec '{spec.name}': formula {e}",
                                    "Write it like ppi(Resolution, Screen (in)) in the formula column of specs.csv."))
                continue
            if spec.name in ds.file_columns:
                issues.append(Issue(WARNING, f"Spec '{spec.name}' has a formula but is also a column of phones.csv.",
                                    "Remove the column from phones.csv (it is calculated) or clear the formula."))
            for a in args:
                # if the values exist, the inputs were there when loading (an input may just be switched off now)
                if a not in ds.phones.columns and spec.name not in ds.phones.columns:
                    issues.append(Issue(ERROR, f"Spec '{spec.name}' is calculated from '{a}', which is not a column.",
                                        "Check the column names inside the formula in specs.csv."))
            continue
        if spec.name not in ds.phones.columns:
            issues.append(Issue(WARNING, f"Spec '{spec.name}' is in specs.csv but not a column of phones.csv.",
                                "Check the spelling (it must match the column title exactly) or remove the row."))
            continue
        if spec.compare not in COMPARE_TYPES:
            issues.append(Issue(ERROR, f"Spec '{spec.name}' has an unknown type '{spec.compare}'.",
                                "Use one of: " + ", ".join(COMPARE_TYPES)))
            continue

        values = ds.phones[spec.name]
        if spec.is_numeric:
            raw = ds.raw[spec.name].to_dict() if ds.raw is not None else {}
            bad = [n for n in ds.names if raw.get(n, "") != "" and pd.isna(values[n])]
            for n in bad:
                issues.append(Issue(WARNING, f"'{n}' → {spec.name} = '{raw[n]}' is not a number.",
                                    "Write only the number (e.g. 1219.5) in phones.csv."))

        if spec.compare == RANKED:
            file = spec.rank_file or f"{slugify(spec.name)}.csv"
            table = ds.ranks.get(spec.name)
            if table is None:
                issues.append(Issue(ERROR, f"Ranked spec '{spec.name}' has no rank file (ranks/{file}).",
                                    f"Create ranks/{file} with columns value,rank,score,details."))
                continue
            missing = sorted({v for v in values if v and not table.has(v)})
            for v in missing:
                used_by = [n for n in ds.names if values[n] == v]
                issues.append(Issue(ERROR, f"{spec.name} '{v}' is not ranked (used by {', '.join(used_by)}).",
                                    f"Add a row to ranks/{table.path.name}: {v},<rank>,<score (optional)>,<details>"))
            no_rank = table.table.index[table.table["rank"].isna()]
            for v in no_rank:
                issues.append(Issue(ERROR, f"'{v}' in ranks/{table.path.name} has no rank number.",
                                    "Fill the rank column (1 = best)."))
    return issues

