# Installing phone-compare with Anaconda (step by step)

You only do steps 1–3 once. After that, generating the report is step 4.

The project gets its **own conda environment** called `phone-compare`. It is a separate, clean
Python with just what this project needs, so it can't break your other projects (or your base
Anaconda), and you can delete it any time.

## 1. Unzip the project
Put the `phone-compare` folder somewhere simple, for example `C:\Users\<you>\Projects\phone-compare`.

## 2. Open the Anaconda Prompt
Start menu → type **Anaconda Prompt** → open it. (Anaconda PowerShell Prompt works too.)
Then go to the project folder:

```
cd C:\Users\<you>\Projects\phone-compare
```

Tip: in File Explorer you can copy the folder path from the address bar.

## 3. Create the environment (once, takes a few minutes)

```
conda env create -f environment.yml
```

This reads `environment.yml` and installs Python 3.12, pandas, matplotlib, jinja2 and pytest
from conda-forge, plus the project itself. When it finishes, check that it works:

```
conda activate phone-compare
phone-compare --version
```

You should see `phone-compare 1.0.0`.

## 4. Use it (every time)

There are two ways, both just a double-click in the project folder:

| Double-click | What it does |
|---|---|
| **`run_app.bat`** | Opens the **app** in your browser: Home, Per spec and Per phone pages, plus tabs to choose **which phones** and **which specs** to compare, **add** phones and **edit** them (✎ Edit in the Phones tab). Keep the black window open while you use it; close it to stop. |
| **`run_report.bat`** | Writes the files in `output\` (CSVs, charts, `report.html`, `report.qmd`) and opens `report.html`. |

`report.html` also has the Phones and Specs tabs (they work without the app); only adding
phones and saving the selection need the app.

**From the Anaconda Prompt:**

```
conda activate phone-compare
cd C:\Users\<you>\Projects\phone-compare
phone-compare
```

Useful options:

```
phone-compare --serve              REM the app (same as run_app.bat)
phone-compare --all                REM ignore the saved selection, use every phone and spec
phone-compare --base "pixel 11"    REM default base for the CSVs and the Quarto report
phone-compare --check              REM only check the data for problems
phone-compare --list               REM show the phone names
phone-compare --csv-sep ";"        REM output CSVs that open directly in Excel/LibreOffice (Spain)
```

In the HTML report you can **change the base phone with the dropdown at the top**: every
table and chart is redrawn. `--base` only sets which one is selected when the page opens (and
the base used in the CSVs and the Quarto report).

## 5. Edit the data
The easiest way is the app (`run_app.bat`): the **Add phone** tab for new ones, **✎ Edit** in the **Phones** tab to correct one. If you type a chipset that
isn't known yet, extra boxes appear to rank it, and it's added to `ranks\chipset.csv` too.

You can also open the CSVs in the `data` folder with LibreOffice/Excel or any text editor:

- `data\phones.csv`: add a row per phone
- `data\specs.csv`: how each column is compared
- `data\ranks\*.csv`: rank lists (add a chipset to `ranks\chipset.csv` and its GPU to `ranks\gpu.csv`)

When saving from LibreOffice/Excel choose **CSV, UTF-8**. Either `,` or `;` as separator works.
Then run step 4 again.

## Optional: PDF report with Quarto
Install Quarto from <https://quarto.org/docs/get-started/>, then:

```
quarto render output\report.qmd --to pdf
```

(The first time, Quarto may ask you to run `quarto install tinytex` for PDF support.)

## Optional: use it from WSL / Linux
Same steps in a terminal where conda is available. Use `./run_report.sh` instead of the `.bat`.

## Maintenance

| I want to… | Command (in Anaconda Prompt) |
|---|---|
| update the environment after `environment.yml` changes | `conda env update -f environment.yml --prune` |
| run the tests | `conda activate phone-compare` then `pytest` |
| see my environments | `conda env list` |
| delete the environment | `conda env remove -n phone-compare` |
| start over from scratch | remove it, then step 3 again |

## Troubleshooting

- **`'phone-compare' is not recognized`**: the environment isn't active. Run `conda activate phone-compare`.
- **`EnvironmentNameNotFound`**: step 3 wasn't done (or failed). Run it again from the project folder.
- **`environment.yml not found`**: you're not in the project folder. Use `cd` to go there first.
- **`run_report.bat` says it can't find Anaconda**: Anaconda is installed somewhere unusual. Use the Anaconda Prompt commands instead.
- **The app says it can't write the file**: `phones.csv` is probably open in Excel, which locks it. Close it and try again.
- **The browser doesn't open with `run_app.bat`**: open <http://127.0.0.1:8765/> yourself (the window shows the exact address).
- **A ⚠ message about the data**: it says exactly which file and row to add (e.g. a chipset missing from `ranks\chipset.csv`).
