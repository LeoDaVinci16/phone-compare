"""Tests for the comparison rules and the data checks (run with: pytest)."""

import csv
import math
import shutil
from datetime import date
from pathlib import Path

import pytest

from phone_compare import compare, find_issues, goodness, load_dataset
from phone_compare.compare import quantity
from phone_compare.data import to_number

DATA = Path(__file__).resolve().parents[1] / "data"
BASE = "Xiaomi Mi 11 Lite"


@pytest.fixture
def ds():
    return load_dataset(DATA)


@pytest.fixture
def tmp_data(tmp_path):
    """A copy of the data folder we can break on purpose."""
    dst = tmp_path / "data"
    shutil.copytree(DATA, dst)
    return dst


def _append_phone(data_dir: Path, values: dict) -> None:
    """Append a row to phones.csv, filling the columns that are not given with ''."""
    path = data_dir / "phones.csv"
    header = next(csv.reader(path.open(encoding="utf-8")))
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerow([values.get(c, "") for c in header])


def test_bundled_data_is_clean(ds):
    assert find_issues(ds) == []


def test_bundled_data_has_22_phones(ds):
    assert len(ds.names) == 22 and ds.names[0] == BASE and "Xiaomi 17" in ds.names


def test_higher_is_better_percent(ds):
    cell = compare(ds, BASE).cells[("Xiaomi 17", "RAM (GB)")]
    assert cell.text == "+100%" and cell.verdict == 1


def test_lower_is_better_flips_the_verdict(ds):
    comp = compare(ds, BASE)
    thinner = comp.cells[("Apple iPhone Air", "Thickness (mm)")]
    thicker = comp.cells[("Google Pixel 10a", "Thickness (mm)")]
    assert thinner.ratio < 0 and thinner.verdict == 1
    assert thicker.ratio > 0 and thicker.verdict == -1


def test_ranked_with_score_gives_percent(ds):
    cell = compare(ds, BASE).cells[("Xiaomi 17", "Chipset")]
    assert math.isclose(cell.ratio, 10806 / 1687 - 1)


def test_ranked_without_score_gives_better_worse(ds):
    comp = compare(ds, BASE)
    assert comp.cells[("Xiaomi 17", "Panel")].text == "better (#1 vs #2)"
    assert comp.cells[("Xiaomi 17", "microSD")].verdict == -1          # the Mi 11 Lite has a card slot


def test_zero_base_says_better_instead_of_percent(ds):
    comp = compare(ds, BASE)                                            # the Mi 11 Lite has no wireless charging
    assert comp.cells[("Xiaomi 17", "Wireless charging (W)")].text == "better (50 vs 0)"
    assert comp.cells[("Xiaomi 17", "Wireless charging (W)")].verdict == 1
    assert comp.cells[("Xiaomi 17T", "Wireless charging (W)")].text == "same"


def test_base_row_is_neutral(ds):
    comp = compare(ds, BASE)
    for spec in ds.columns("higher", "lower", "ranked"):
        v = comp.cells[(BASE, spec)].verdict
        assert math.isnan(v) or v == 0


def test_changing_the_base(ds):
    comp = compare(ds, "Apple iPhone 18 Pro")
    assert comp.cells[(BASE, "Price (€)")].verdict == 1            # the Mi 11 Lite is cheaper than the iPhone 18 Pro


def test_chipset_sorted_low_to_high(ds):
    order = list(quantity(ds, "Chipset").sort_values().index)
    assert order[0] == BASE and ds.phones.at[order[-1], "Chipset"] == "Apple A20 Pro"


def test_goodness_range(ds):
    g = goodness(ds)
    assert g.min().min() >= 0 and g.max().max() <= 100
    assert g.at[BASE, "Price (€)"] == 100                               # cheapest


def test_unranked_chipset_is_reported(tmp_data):
    _append_phone(tmp_data, {"Phone": "New phone", "Price (€)": "500", "Chipset": "Snapdragon 8 Elite Gen 6"})
    ds = load_dataset(tmp_data)
    messages = [i.message for i in find_issues(ds)]
    assert any("Snapdragon 8 Elite Gen 6" in m and "not ranked" in m for m in messages)
    assert compare(ds, BASE).cells[("New phone", "Chipset")].status == "missing"


def test_column_without_type_is_reported(tmp_data):
    path = tmp_data / "phones.csv"
    rows = list(csv.reader(path.open(encoding="utf-8")))
    rows = [rows[0] + ["Colour"]] + [r + ["Black"] for r in rows[1:]]
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)
    assert any("'Colour'" in i.message and "no type" in i.message for i in find_issues(load_dataset(tmp_data)))


def test_missing_rank_file_is_reported(tmp_data):
    (tmp_data / "ranks" / "panel.csv").unlink()
    assert any("no rank file" in i.message for i in find_issues(load_dataset(tmp_data)))


@pytest.mark.parametrize("text,expected", [("1219", 1219), ("1219.5", 1219.5), ("1219,5", 1219.5),
                                           ("1.219,50", 1219.5), ("1 219 €", 1219), ("", math.nan)])
def test_to_number(text, expected):
    got = to_number(text)
    assert (math.isnan(got) and math.isnan(expected)) or got == expected


def test_plus_models_get_their_own_chart_file():
    from phone_compare.data import slugify

    assert slugify("Redmi Note 15 Pro+ 5G") != slugify("Redmi Note 15 Pro 5G")


def test_html_report_has_every_base(ds, tmp_path):
    from phone_compare.report import report_data, write_html

    data = report_data(ds, BASE)
    assert set(data["comp"]) == set(ds.names)              # one precomputed comparison per possible base
    assert data["comp"]["Xiaomi 17"][BASE]["Chipset"][1] == -1   # vs the Xiaomi 17, the Mi 11 Lite's chipset is worse
    html = write_html(ds, compare(ds, BASE), [], None, tmp_path / "r.html").read_text(encoding="utf-8")
    assert 'id="base"' in html and "const DATA" in html


def test_messy_csv_from_a_spreadsheet(tmp_path):
    """Extra empty columns, empty rows, ';' separator, Windows encoding: all must load."""
    from phone_compare.data import read_csv

    p = tmp_path / "x.csv"
    p.write_bytes("Phone;Price (€);Chipset;\r\nA;1.219,50;X;;;\r\n;;;\r\nB;999;Y\r\n\r\n".encode("cp1252"))
    df = read_csv(p)
    assert list(df.columns) == ["Phone", "Price (€)", "Chipset"]
    assert df["Phone"].tolist() == ["A", "B"]


def test_values_in_an_untitled_column_give_a_clear_error(tmp_path):
    from phone_compare.data import DataFileError, read_csv

    p = tmp_path / "x.csv"
    p.write_text("Phone,Price\nA,1,oops\n", encoding="utf-8")
    with pytest.raises(DataFileError, match="more values than there are column titles"):
        read_csv(p)


# ---------------------------------------------------------------- selection and adding phones

def test_selection_switches_phones_and_specs_off(tmp_data):
    from phone_compare.data import apply_selection, load_selection, save_selection

    save_selection(tmp_data, {"phones_off": ["Nope?", "OnePlus 15"], "specs_off": ["Resolution"]})
    ds = load_dataset(tmp_data)
    sub = apply_selection(ds, load_selection(tmp_data))
    assert "OnePlus 15" not in sub.names and "Resolution" not in sub.phones.columns
    assert find_issues(sub) == []          # a switched-off spec must not raise "not a column" warnings


def test_add_phone_with_a_new_chipset(tmp_data):
    from phone_compare.editing import add_phone

    msgs = add_phone(tmp_data, {"Phone": "Test 18", "Price (€)": "1.099,50", "Chipset": "Snapdragon 8 Elite Gen 6",
                                "Weight (g)": "190,5", "Notes": "has, a comma"},
                     {"Chipset": {"rank": "1", "score": "12500", "details": "estimate"}})
    assert any("Added 'Test 18'" in m for m in msgs)
    ds = load_dataset(tmp_data)
    assert ds.phones.at["Test 18", "Price (€)"] == 1099.5 and ds.phones.at["Test 18", "Notes"] == "has, a comma"
    assert ds.ranks["Chipset"].score("Snapdragon 8 Elite Gen 6") == 12500
    assert find_issues(ds) == []


def test_add_phone_refuses_duplicates_and_bad_numbers(tmp_data):
    from phone_compare.editing import AddPhoneError, add_phone

    with pytest.raises(AddPhoneError, match="already"):
        add_phone(tmp_data, {"Phone": BASE})
    with pytest.raises(AddPhoneError, match="not a number"):
        add_phone(tmp_data, {"Phone": "X", "Price (€)": "cheap"})
    with pytest.raises(AddPhoneError, match="needs a name"):
        add_phone(tmp_data, {"Price (€)": "1000"})


def test_unranked_value_without_rank_is_reported_after_adding(tmp_data):
    from phone_compare.editing import add_phone

    msgs = add_phone(tmp_data, {"Phone": "Y", "Chipset": "Apple A21 Pro"})
    assert any("Still to do" in m and "Apple A21 Pro" in m for m in msgs)


def test_edit_phone_replaces_only_its_row(tmp_data):
    from phone_compare.data import load_selection, save_selection
    from phone_compare.editing import update_phone

    old = "OnePlus 15"
    save_selection(tmp_data, {"phones_off": [old], "specs_off": []})
    before = load_dataset(tmp_data)
    values = {c: before.raw.at[old, c] for c in before.phones.columns}
    values.update({"Phone": "OnePlus 15 (16/512)", "Price (€)": "1.049,00"})
    msgs = update_phone(tmp_data, old, values)
    assert any("Renamed" in m for m in msgs)
    after = load_dataset(tmp_data)
    assert after.names.index("OnePlus 15 (16/512)") == before.names.index(old)   # same position
    assert after.phones.at["OnePlus 15 (16/512)", "Price (€)"] == 1049
    assert len(after.names) == len(before.names)
    assert load_selection(tmp_data)["phones_off"] == ["OnePlus 15 (16/512)"]     # selection follows the rename
    other = "Xiaomi 17"
    assert after.raw.loc[other].tolist() == before.raw.loc[other].tolist()        # other rows untouched


def test_edit_refuses_taking_another_phones_name(tmp_data):
    from phone_compare.editing import AddPhoneError, update_phone

    with pytest.raises(AddPhoneError, match="already"):
        update_phone(tmp_data, "OnePlus 15", {"Phone": BASE})


def test_save_by_name_replaces_or_adds(tmp_data):
    from phone_compare.editing import save_phone

    before = load_dataset(tmp_data)
    name = "Poco F8 Pro"
    values = {c: before.raw.at[name, c] for c in before.file_columns} | {"Phone": name, "Price (€)": "599"}
    assert "Updated" in save_phone(tmp_data, values)[0]                 # same name -> replaced
    after = load_dataset(tmp_data)
    assert len(after.names) == len(before.names) and after.phones.at[name, "Price (€)"] == 599
    assert "Added" in save_phone(tmp_data, values | {"Phone": "Poco copy"})[0]   # new name -> added
    assert len(load_dataset(tmp_data).names) == len(before.names) + 1


# ---------------------------------------------------------------- calculated specs (formula column of specs.csv)

def test_ppi_is_calculated_after_its_inputs(ds):
    cols = list(ds.phones.columns)
    assert cols.index("Pixel density (ppi)") == max(cols.index("Resolution"), cols.index("Screen (in)")) + 1
    assert "Pixel density (ppi)" not in ds.file_columns
    assert ds.phones.at[BASE, "Pixel density (ppi)"] == 402            # 1080×2400 on 6.55" (GSMArena: ~402 ppi)


def test_update_years_left_counts_from_today(ds):
    assert ds.phones.at[BASE, "Update years left"] == 0                # support ended in 2024: never negative
    assert ds.phones.at["Samsung Galaxy S26", "Update years left"] == max(0, 2033 - date.today().year)
    assert "Update years left" not in ds.file_columns


def test_calculated_spec_is_never_written_to_the_csv(tmp_data):
    from phone_compare.editing import save_phone

    ds = load_dataset(tmp_data)
    name = ds.names[0]
    values = {ds.name_column: name, **{c: ds.raw.at[name, c] for c in ds.file_columns}}
    values["Pixel density (ppi)"] = "999"
    header_before = (tmp_data / "phones.csv").read_text(encoding="utf-8").splitlines()[0]
    save_phone(tmp_data, values)
    assert (tmp_data / "phones.csv").read_text(encoding="utf-8").splitlines()[0] == header_before
    assert load_dataset(tmp_data).phones.at[name, "Pixel density (ppi)"] != 999


def test_bad_formula_is_reported(tmp_data):
    path = tmp_data / "specs.csv"
    path.write_text(path.read_text(encoding="utf-8").replace("ppi(Resolution, Screen (in))", "ppi(Resolution, Nope)"),
                    encoding="utf-8")
    msgs = [i.message for i in find_issues(load_dataset(tmp_data))]
    assert any("'Nope'" in m for m in msgs)
