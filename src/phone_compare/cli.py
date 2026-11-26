"""Command line.

    phone-compare                      build the CSVs, charts and reports into output/
    phone-compare --serve              app mode: open the report in the browser, with editing
    phone-compare --check              only check the data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .compare import compare
from .data import DataFileError, apply_selection, load_dataset, load_selection
from .validate import ERROR, find_issues

FORMATS = ("html", "qmd", "md")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phone-compare",
        description="Compare phones spec by spec against a base phone. "
                    "Writes comparison CSVs, charts and a report, or runs the app (--serve).")
    p.add_argument("--data", default="data", type=Path,
                   help="folder with phones.csv, specs.csv and ranks/ (default: data)")
    p.add_argument("--base", help="phone to compare against (part of the name is enough; default: first one)")
    p.add_argument("--out", default="output", type=Path, help="output folder (default: output)")
    p.add_argument("--format", nargs="+", choices=FORMATS, default=["html", "qmd"],
                   help="report formats (default: html qmd)")
    p.add_argument("--csv-sep", default=",", help="separator for the output CSVs (use ';' for Excel in Spain)")
    p.add_argument("--no-plots", action="store_true", help="skip the PNG charts (faster)")
    p.add_argument("--all", action="store_true",
                   help="ignore data/selection.json and use every phone and spec")
    p.add_argument("--list", action="store_true", help="list the phones and exit")
    p.add_argument("--check", action="store_true", help="only check the data for problems and exit")
    p.add_argument("--strict", action="store_true", help="stop with an error if the data has problems")
    p.add_argument("--serve", action="store_true", help="app mode: open the report in your browser with editing")
    p.add_argument("--port", type=int, default=8765, help="port for --serve (default: 8765)")
    p.add_argument("--no-browser", action="store_true", help="with --serve: don't open the browser automatically")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def resolve_base(names: list[str], wanted: str | None) -> str | None:
    """Exact name, or a unique part of a name (case-insensitive). None if not found / ambiguous."""
    if not wanted:
        return names[0]
    if wanted in names:
        return wanted
    matches = [n for n in names if wanted.lower() in n.lower()]
    return matches[0] if len(matches) == 1 else None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        full = load_dataset(args.data)
    except FileNotFoundError as e:
        print(f"Could not find a data file: {e.filename}\n"
              f"Check that --data points to the folder with phones.csv and specs.csv.", file=sys.stderr)
        return 2
    except DataFileError as e:
        print(f"Problem in the data: {e}", file=sys.stderr)
        return 2

    if args.list:
        sel = load_selection(args.data)
        for i, name in enumerate(full.names, 1):
            print(f"{i:>3}. {name}{'   (switched off)' if name in sel['phones_off'] else ''}")
        return 0

    if args.serve:
        from .server import serve

        base = resolve_base(full.names, args.base) if args.base else None
        return serve(args.data, args.out, base=base, port=args.port, open_browser=not args.no_browser)

    # which phones/specs to use (data/selection.json, unless --all)
    selection = {"phones_off": [], "specs_off": []} if args.all else load_selection(args.data)
    ds = apply_selection(full, selection)
    off_l, off_s = len(full.names) - len(ds.names), len(full.phones.columns) - len(ds.phones.columns)
    if off_l or off_s:
        print(f"Using data/selection.json: {off_l} phone(s) and {off_s} spec(s) switched off (--all to ignore).")

    issues = find_issues(ds)
    if issues:
        print(f"Found {len(issues)} thing(s) to fix in the data:\n")
        for issue in issues:
            print(issue)
        print()
    else:
        print("✅ Data OK: every spec has a type and every ranked value has a rank.")
    if args.check:
        return 1 if any(i.level == ERROR for i in issues) else 0
    if args.strict and any(i.level == ERROR for i in issues):
        print("Stopping because of --strict.", file=sys.stderr)
        return 1

    base = resolve_base(ds.names, args.base)
    if base is None:
        print(f"Base '{args.base}' not found among the selected phones. Use --list to see the names.", file=sys.stderr)
        return 2

    comp = compare(ds, base)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    from .report import write_csvs, write_html, write_markdown

    written = write_csvs(ds, comp, out, sep=args.csv_sep)
    plots: dict = {}
    if not args.no_plots:
        from .plots import make_all

        plots = make_all(ds, comp, out)
    if "html" in args.format:      # the HTML gets every phone, with the selection pre-applied (changeable in the page)
        written.append(write_html(full, compare(full, base), issues, plots, out / "report.html", selection=selection))
    if "qmd" in args.format:
        written.append(write_markdown(ds, comp, issues, plots, out / "report.qmd", quarto=True))
    if "md" in args.format:
        written.append(write_markdown(ds, comp, issues, plots, out / "report.md", quarto=False))

    n_plots = (1 if plots.get("overview") else 0) + len(plots.get("specs", {})) + len(plots.get("phones", {}))
    print(f"Base: {base}")
    for p in written:
        print(f"  wrote {p}")
    if n_plots:
        print(f"  wrote {n_plots} charts in {out / 'plots'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
