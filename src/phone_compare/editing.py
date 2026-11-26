"""Add a phone (and new rank values, e.g. a new chipset) to the CSV files.

Rows are *appended* to the end of the existing files, keeping their separator and encoding,
so whatever formatting your spreadsheet app saved is left untouched.
"""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path

from .data import RANKED, _detect_sep, load_dataset, slugify, to_number


class AddPhoneError(ValueError):
    """The phone can't be added; the message says why."""


def _file_format(path: Path) -> tuple[str, str]:
    """(encoding, separator) of an existing CSV, so appended rows match it."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
        enc = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
        enc = "cp1252"
    first = next((ln for ln in text.splitlines() if ln.strip(" ,;\t")), "")
    return enc, _detect_sep(first)


def _append_row(path: Path, values: list[str], header: list[str] | None = None) -> None:
    """Append one CSV row (creating the file with `header` if it doesn't exist)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        enc, sep = "utf-8", ","
        buf = io.StringIO()
        csv.writer(buf, delimiter=sep, lineterminator="\n").writerow(header or [])
        path.write_text(buf.getvalue(), encoding=enc)
    enc, sep = _file_format(path)
    existing = path.read_bytes()
    buf = io.StringIO()
    csv.writer(buf, delimiter=sep, lineterminator="\r\n" if b"\r\n" in existing else "\n").writerow(values)
    with open(path, "a", encoding=enc, newline="") as f:
        if existing and not existing.endswith((b"\n", b"\r")):
            f.write("\r\n" if b"\r\n" in existing else "\n")
        f.write(buf.getvalue())


def _clean_number(text: str) -> str:
    """'1.219,50' -> '1219.5'  ('' stays ''). Raises if it isn't a number."""
    if not text.strip():
        return ""
    n = to_number(text)
    if math.isnan(n):
        raise ValueError(text)
    return f"{n:g}" if abs(n) < 1e15 else str(n)


def _build_row(ds, values: dict[str, str], original: str | None = None) -> list[str]:
    """Check the form values and return the CSV row (name first, then every column in file order)."""
    name = values.get(ds.name_column, "")
    if not name:
        raise AddPhoneError("The phone needs a name.")
    if name in ds.names and name != original:
        raise AddPhoneError(f"There is already a phone called '{name}'. Use a different name (add the model code).")
    row, errors = [name], []
    for col in ds.file_columns or ds.phones.columns:      # calculated specs (formula) are never written
        v = values.get(col, "")
        spec = ds.specs.get(col)
        if spec is not None and spec.is_numeric:
            try:
                v = _clean_number(v)
            except ValueError:
                errors.append(f"{col}: '{v}' is not a number")
        row.append(v)
    if errors:
        raise AddPhoneError("Please fix: " + "; ".join(errors))
    return row


def _add_new_ranks(ds, data_dir: Path, values: dict[str, str], new_ranks: dict[str, dict]) -> list[str]:
    """Append ranked values that are new (e.g. a new chipset) to their rank file."""
    messages = []
    for spec_name, info in new_ranks.items():
        spec = ds.specs.get(spec_name)
        value = values.get(spec_name, "")
        rank_text = str(info.get("rank", "")).strip()
        if not value or not rank_text or spec is None or spec.compare != RANKED:
            continue
        table = ds.ranks.get(spec_name)
        if table is not None and table.has(value):
            continue
        try:
            rank = _clean_number(rank_text)
            score = _clean_number(str(info.get("score", "")))
        except ValueError:
            raise AddPhoneError(f"{spec_name}: rank and score must be numbers.") from None
        path = table.path if table is not None else data_dir / "ranks" / (spec.rank_file or f"{slugify(spec_name)}.csv")
        _append_row(path, [value, rank, score, str(info.get("details", "")).strip()],
                    header=["value", "rank", "score", "details"])
        messages.append(f"Added {spec_name} '{value}' to ranks/{path.name} with rank {rank}"
                        + (f" and score {score}" if score else "") + ".")
    return messages


def _still_to_do(data_dir: Path, name: str) -> list[str]:
    from .validate import find_issues

    return [f"Still to do: {i.message} → {i.fix}" for i in find_issues(load_dataset(data_dir))
            if f"used by {name}" in i.message or f"'{name}'" in i.message]


def add_phone(data_dir: str | Path, values: dict[str, str], new_ranks: dict[str, dict] | None = None) -> list[str]:
    """Append a phone to phones.csv.

    values     {column title: value}; the phone name goes under the first column's title.
    new_ranks  {spec: {"rank": "3", "score": "700", "details": "..."}} for ranked values that are not
               in their rank file yet (e.g. a new chipset). They are appended to ranks/<file>.csv.

    Returns a list of messages (what was done, plus anything still to fix).
    """
    data_dir = Path(data_dir)
    ds = load_dataset(data_dir)
    values = {k: str(v).strip() for k, v in values.items() if v is not None}
    row = _build_row(ds, values)
    messages = _add_new_ranks(ds, data_dir, values, new_ranks or {})
    _append_row(data_dir / "phones.csv", row)
    return [f"Added '{row[0]}' to phones.csv.", *messages, *_still_to_do(data_dir, row[0])]


def save_phone(data_dir: str | Path, values: dict[str, str], new_ranks: dict[str, dict] | None = None) -> list[str]:
    """What the app's form does: save by name.

    * the name already exists -> that phone's row is replaced with the new values
    * the name is new          -> a new phone is added at the end
    """
    data_dir = Path(data_dir)
    ds = load_dataset(data_dir)
    values = {k: str(v).strip() for k, v in values.items() if v is not None}
    name = values.get(ds.name_column, "")
    if name and name in ds.names:
        row = _build_row(ds, values, original=name)
        messages = _add_new_ranks(ds, data_dir, values, new_ranks or {})
        _replace_row(data_dir / "phones.csv", name, row)
        return [f"Updated '{name}': its data in phones.csv was replaced.", *messages, *_still_to_do(data_dir, name)]
    return add_phone(data_dir, values, new_ranks)


def update_phone(data_dir: str | Path, original: str, values: dict[str, str],
                  new_ranks: dict[str, dict] | None = None) -> list[str]:
    """Replace the row of phone `original` in phones.csv with the new values (it can be renamed).
    The rest of the file (other rows, separator, encoding) is kept as it is."""
    data_dir = Path(data_dir)
    ds = load_dataset(data_dir)
    if original not in ds.names:
        raise AddPhoneError(f"'{original}' is no longer in phones.csv (was it renamed or removed?). Refresh the page.")
    values = {k: str(v).strip() for k, v in values.items() if v is not None}
    row = _build_row(ds, values, original=original)
    messages = _add_new_ranks(ds, data_dir, values, new_ranks or {})
    _replace_row(data_dir / "phones.csv", original, row)
    if row[0] != original:                      # keep the saved selection pointing at the new name
        from .data import SELECTION_FILE, load_selection, save_selection

        if (data_dir / SELECTION_FILE).exists():
            sel = load_selection(data_dir)
            sel["phones_off"] = [row[0] if n == original else n for n in sel["phones_off"]]
            save_selection(data_dir, sel)
        messages.insert(0, f"Renamed '{original}' to '{row[0]}'.")
    return [f"Saved the changes to '{row[0]}' in phones.csv.", *messages, *_still_to_do(data_dir, row[0])]


def _replace_row(path: Path, name: str, new_row: list[str]) -> None:
    """Rewrite phones.csv with the record whose first cell is `name` replaced."""
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    enc, sep = _file_format(path)
    text = raw.decode("utf-8-sig" if enc == "utf-8" else enc, errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    records = list(csv.reader(io.StringIO(text), delimiter=sep))
    header_seen = False
    for i, rec in enumerate(records):
        if not any(c.strip() for c in rec):
            continue
        if not header_seen:
            header_seen = True
            continue
        if rec[0].strip() == name:
            records[i] = new_row + [""] * max(0, len(rec) - len(new_row))
            break
    else:
        raise AddPhoneError(f"Could not find '{name}' in {path.name}.")
    buf = io.StringIO()
    csv.writer(buf, delimiter=sep, lineterminator=newline).writerows(records)
    out = buf.getvalue()
    if not text.endswith(("\n", "\r")):
        out = out.rstrip("\r\n")
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + out.encode(enc))
