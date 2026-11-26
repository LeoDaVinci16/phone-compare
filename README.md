# phone-compare

Compare phones spec by spec against a **base phone** (the one you have now, or any other).
It is the phone version of [laptop-compare](https://github.com/LeoDaVinci16/laptop-compare) and works the same way,
from CSV files:

- `output/comparison.csv`: the comparison table (`+70%`, `better (#1 vs #2)`, …)
- `output/report.html`: one self-contained, interactive report: pick the base phone in the page
- `output/report.qmd`: the same report for Quarto (`quarto render report.qmd --to pdf`)
- `output/plots/*.png`: the same charts as images (used by the Quarto report)

**Live report:** https://leodavinci16.github.io/phone-compare/ (once the repo is on GitHub with Pages switched on,
see below). Explore the data online (read-only). To add or edit phones, download the project and run it locally.

> **Built mostly by Claude** (an AI model by Anthropic). I had the idea, wrote the requirements and
> tested the result; Claude wrote most of the code. The phone data (prices, specs, benchmark scores)
> was also collected by Claude from GSMArena, shop listings and benchmark sites in November 2026: it can be
> out of date or wrong, so check it before buying anything.

## The phones in `data/phones.csv`
22 phones, with the **Xiaomi Mi 11 Lite** first (so it is the default base) and the **Xiaomi 17**:

| Range | Phones |
|---|---|
| Xiaomi / Poco / Redmi | Mi 11 Lite, Xiaomi 17, 17 Ultra, 17T Pro, 17T, Poco F8 Pro, Poco X8 Pro, Redmi Note 15 Pro+ 5G, Redmi Note 15 Pro 5G |
| Samsung | Galaxy S26 (Exynos 2600, the Spanish version), Galaxy S26 Ultra, Galaxy A57 |
| Google | Pixel 11, Pixel 10a |
| Apple | iPhone 17, iPhone 18 Pro, iPhone Air, iPhone 17e |
| Others | OnePlus 15, Nothing Phone (4a), Motorola Edge 70, Fairphone (Gen. 6) |

Each row is the **base version** (RAM/storage) at the price shown; `Price seen at` says where the price comes from.

## Use it with your own phones
Download the project (green **Code** button → *Download ZIP*, or `git clone`), install it (below) and edit
`data/phones.csv` and the rank files offline, or use the app's **Add phone** / **✎ Edit** forms.

## Contributing / contact
Want to turn it into a JavaScript-only website, host the app on a server, or improve it some other way?
Get in touch at **arnaucnadal@disroot.org**. I'm happy to give permission.

## License
[MIT](LICENSE): free to use, copy, change and share, as long as the license text stays with it.
The phone data in `data/` (prices, specs, benchmark scores) is provided as is, with no guarantee
that it is correct or up to date.

## Website (GitHub Pages)
The online version is just a copy of the report in `docs/index.html`, served by GitHub Pages
(*Settings → Pages → Deploy from a branch → main / docs*). To update it after changing the data:
double-click `run_publish.bat` (or `./run_publish.sh`), then commit and push the `docs` folder.

## Install (Anaconda)

Full beginner steps are in **[INSTALL.md](INSTALL.md)**. In short, from the Anaconda Prompt inside this folder:

```
conda env create -f environment.yml      # once
conda activate phone-compare
phone-compare                            # writes output/ (or double-click run_report.bat)
```

## Run

```bash
phone-compare                                   # base = first phone in phones.csv
phone-compare --base "pixel 11"                 # part of the name is enough if it's unique
phone-compare --list                            # show the phone names
phone-compare --check                           # only check the data (alerts), write nothing
phone-compare --format html qmd md              # choose report formats (default: html qmd)
phone-compare --csv-sep ";"                     # CSVs that Excel/LibreOffice in Spain open directly
phone-compare --data other_folder --out results
```

### App mode (add phones, choose phones and specs)

```
phone-compare --serve          # or double-click run_app.bat
```

Opens the report in your browser from a small local web server (Python's built-in one,
listening only on this computer). The page has these tabs:

| Tab | What it does |
|---|---|
| **Home** | entrance page: base phone, key numbers, highlights, then summary, comparison, values and overview |
| **Per spec** | one chart per spec, selected phones sorted low → high |
| **Per phone** | each phone vs the base (advantage bars + radar), with a "jump to" menu |
| **Phones** | tick/untick phones to keep charts readable or narrow down to finalists; **✎ Edit** opens a phone in the form to correct it |
| **Specs** | tick/untick the specs that matter to you (e.g. drop Brightness); scores and "best" update too |
| **Add phone** | a form with one box per spec; new chipsets/ranked values can be ranked right there (also used for editing) |

Editing replaces only that phone's row in `phones.csv` (renaming works; the saved selection follows the new name).

**Save as default** writes the ticks to `data/selection.json` (it lists what is switched *off*,
so new phones and specs appear switched on). The CSVs and the Quarto report also use it;
`--all` ignores it. Rows are appended to the CSVs, keeping their separator and encoding.

The static `output/report.html` has the same tabs: ticking works there too, but adding
phones and saving need app mode.

### Changing the base phone
- **In the HTML report:** use the **Base phone** dropdown at the top. The comparison table,
  every chart and every phone card are redrawn instantly; no Python needed. The choice is
  kept in the address (`report.html#base=...`), so you can bookmark it.
- **On the command line:** `--base` chooses the base for the CSVs and the Quarto/Markdown
  report, and which phone the HTML opens with.

## The data (folder `data/`)

The files can use `,` or `;` as separator and `1219.5` or `1219,5` for decimals. Save them as UTF-8.

### `phones.csv`: one row per phone
The first column is the phone name, and every other column is a spec. **To add a phone, add a row.**
To add a spec, add a column, then describe it in `specs.csv`.

### `specs.csv`: how each column is compared
| spec | compare | rank_file | notes | formula |
|---|---|---|---|---|
| Price (€) | lower | | | |
| Chipset | ranked | chipset.csv | Score = Geekbench 6 multi-core | |
| Battery (mAh) | higher | | | |
| Main sensor (1/x in) | lower | | smaller x = bigger sensor | |
| Pixel density (ppi) | higher | | Sharpness | ppi(Resolution, Screen (in)) |
| Update years left | higher | | | years_left(Updates until) |
| Notes | info | | | |

`compare` is one of:
- `higher`: a bigger number is better (RAM, battery, charging watts)
- `lower`: a smaller number is better (price, weight, thickness, the x in a 1/x″ sensor)
- `ranked`: text values sorted in a rank file (chipset, GPU, panel, water resistance…)
- `info`: shown but not compared (notes, shop, screen size)

`formula` (optional) makes a **calculated spec**: it is not a column of `phones.csv`, it's worked out
from other columns and shown right after them. The app's form shows it greyed out. Available formulas:
- `ppi(<resolution column>, <screen size column>)`: pixels per inch, e.g. 1080×2400 on 6.55" → 402
- `years_left(<year column>)`: years from today until that year (never below 0), e.g. updates until 2032 → 6 in 2026.
  It updates itself every year, so `Updates until` never needs editing.

### Specs used for phones
Price · Chipset (Geekbench 6 multi-core) · GPU (3DMark Wild Life Extreme) · RAM · Storage · microSD ·
Battery · Charging · Wireless charging · Weight · Thickness · Screen size (info) · Panel · Resolution (info) →
Pixel density · Refresh rate · Brightness · Main camera MP · Main sensor size · OIS · Optical zoom · Ultrawide MP ·
Selfie MP · Video · Water resistance · 5G · Wi-Fi · USB · Stereo speakers · OS · Updates until (info) →
Update years left · Released, Price seen at, Notes (info).

Conventions: `0` means "doesn't have it" (no wireless charging, no ultrawide); an optical zoom of `1` means no
telephoto camera; brightness is the maker's peak claim, so real-world brightness can be much lower.

### `ranks/<file>.csv`: one file per ranked spec
```csv
value,rank,score,details
Apple A20 Pro,1,12800,"Geekbench 6 multi 12800 · iPhone 18 Pro ..."
Snapdragon 8 Elite Gen 5 for Galaxy,2,11566,...
```
- `value`: exactly as written in `phones.csv`
- `rank`: 1 = best (equal ranks are fine)
- `score`: optional. If both phones' values have a score, the comparison is a % (chipset: "+70%");
  otherwise it is `better/same/worse (#rank vs #rank)`.
- `details`: free text, shown in each phone's section of the report (here: where each benchmark score comes from)

Benchmark sources: GSMArena's own tests where they exist (one score per chipset/GPU; where several phones share
a chip, the average); otherwise UL's 3DMark database, PhoneArena, 91mobiles, Tom's Guide or Notebookcheck, as
written in each row's `details`.

**Adding a new chipset:** add one row to `ranks/chipset.csv` with its name, rank and (optionally) score,
and one to `ranks/gpu.csv` for its GPU.

## Alerts
Every run checks the data and tells you exactly what to add. For example:

```
⚠ Chipset 'Snapdragon 8 Elite Gen 6' is not ranked (used by New phone).
    → Add a row to ranks/chipset.csv: Snapdragon 8 Elite Gen 6,<rank>,<score (optional)>,<details>
```

It also catches a column with no row in `specs.csv`, a ranked spec without a rank file, numbers
that aren't numbers, and duplicated phone names. In the report, cells that are affected turn orange.
`--strict` stops the run when there are errors, and `--check` returns exit code 1 (useful in scripts).

## How the comparison works
| spec type | cell shows | green when |
|---|---|---|
| higher | % vs base | the phone has more |
| lower | % vs base | the phone has less (cheaper, lighter, thinner, bigger sensor) |
| higher/lower, base is 0 | better / same / worse (value vs 0) | e.g. it has wireless charging and the base doesn't |
| ranked + score | % of the scores | higher score |
| ranked | better / same / worse (#rank vs #rank) | better rank |
| info | the value | not compared |

The charts and the heatmap use a **0–100 score per spec** within the list (100 = best phone
for that spec, 0 = worst). Ranked specs without scores are scored by rank.

### Charts
- **Per spec** (`plots/spec_*.png`): every phone sorted low → high (price from cheap to expensive
  as a line plot, chipset from slow to fast as bars, ranked specs as tiers). The base is orange.
- **Per phone** (`plots/phone_*.png`): on the left, how much better or worse it is than the base
  for each spec; on the right, a radar chart of its 0–100 scores against the base.
- **Overview** (`plots/overview_heatmap.png`): every phone × every spec.

## Output CSVs
| file | content |
|---|---|
| `comparison.csv` | the table as you read it (`+70%`, `better (#1 vs #2)`) |
| `comparison_ratios.csv` | % differences as numbers (0.7 = +70%) |
| `comparison_verdicts.csv` | +1 better / 0 same / −1 worse (already accounts for lower-is-better) |
| `scores_0_100.csv` | the heatmap values |

## Project layout
```
src/phone_compare/
  data.py        load the CSVs (separator and decimal detection, number parsing, calculated specs)
  validate.py    alerts: missing types, unranked values, missing rank files...
  compare.py     comparison rules, sorting (low → high), 0–100 scores, best per spec
  plots.py       charts (matplotlib)
  report.py      CSVs, interactive HTML report (template + charts in templates/report.html.j2),
                 Quarto/Markdown report
  editing.py     add a phone / new rank values to the CSVs
  server.py      app mode (local web server, standard library only)
  cli.py         command line
tests/           pytest tests for the rules and the alerts
```

## Tests
```bash
conda activate phone-compare
pytest
```
