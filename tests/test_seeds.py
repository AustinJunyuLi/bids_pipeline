from pipeline.seeds import canonical_deal_slug, make_slug


def test_slug_basic():
    assert make_slug("Imprivata, Inc.") == "imprivata-inc"


def test_slug_ampersand():
    assert (
        make_slug("Providence & Worcester Railroad Co/RI/")
        == "providence-worcester-railroad-co-ri"
    )


def test_slug_strips_trailing_hyphens():
    slug = make_slug("PetSmart, Inc.")
    assert not slug.endswith("-")


def test_canonical_slug_overrides_known_reference_names():
    assert canonical_deal_slug("IMPRIVATA INC") == "imprivata"
    assert canonical_deal_slug("PROVIDENCE & WORCESTER RR CO") == "providence-worcester"
    assert canonical_deal_slug("S T E C INC") == "stec"
