import pytest

from atlas.taxonomy import OTHER_ID, load_taxonomy, parse_taxonomy


def test_counts_10_sectors_50_fields():
    tax = load_taxonomy()
    assert tax.version == 3
    assert len(tax.sectors) == 10
    assert len(tax.fields) == 50
    assert tax.summary() == "Taxonomy v3: 10 sectors / 50 fields"


def test_ids_unique_and_nested():
    tax = load_taxonomy()
    ids = [f.id for f in tax.fields]
    assert len(ids) == len(set(ids))
    for s in tax.sectors:
        assert all(f.id.startswith(s.id + ".") for f in s.fields)


def test_new_sectors_present():
    tax = load_taxonomy()
    assert tax.name_of("S09") == "Smart City & Intelligent Transportation"
    assert tax.name_of("S10") == "Entrepreneurship & Startup Pipeline"
    assert len(tax.sectors[2].fields) == 6  # S03 has six fields


def test_lookups_and_other():
    tax = load_taxonomy()
    assert tax.sector_of("S05.4") == "S05"
    assert tax.sector_of(OTHER_ID) == OTHER_ID
    assert OTHER_ID in tax.sector_ids and OTHER_ID in tax.field_ids
    assert tax.name_of(OTHER_ID) == "Other / Unclear"
    with pytest.raises(KeyError):
        tax.sector_of("S99.1")


def test_parse_rejects_misplaced_field():
    bad = {"version": 1, "sectors": [{"id": "S01", "name": "A", "fields": [{"id": "S02.1", "name": "x"}]}]}
    with pytest.raises(ValueError):
        parse_taxonomy(bad)


def test_parse_rejects_duplicates():
    bad = {"version": 1, "sectors": [
        {"id": "S01", "name": "A", "fields": [{"id": "S01.1", "name": "x"}, {"id": "S01.1", "name": "y"}]}]}
    with pytest.raises(ValueError):
        parse_taxonomy(bad)
