import pytest

from pipeline import normalize as n


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Fr.", ("FR", 0)),
        ("R-So.", ("SO", 1)),
        ("R-Sr.", ("SR", 1)),
        ("Gr.", ("GR", 0)),
        ("Redshirt Junior", ("JR", 1)),
        (None, (None, 0)),
        ("??", (None, 0)),
    ],
)
def test_parse_class(raw, expected):
    assert n.parse_class(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Antioch, Calif.", ("Antioch", "CA")),
        ("Paterson, NJ", ("Paterson", "NJ")),
        ("Knoxville, Tennessee", ("Knoxville", "TN")),
        ("Chattanooga, T.N.", ("Chattanooga", "TN")),
        ("Rock Hill, S.C. (Northwestern", ("Rock Hill", "SC")),
        ("Murfreesboro", ("Murfreesboro", None)),
        ("Brampton, Ontario (Canada)", ("Brampton", "Ontario (Canada)")),
        (None, (None, None)),
    ],
)
def test_parse_hometown(raw, expected):
    assert n.parse_hometown(raw) == expected


def test_name_key_folds_punctuation_suffix_and_accents():
    assert n.name_key("A.J.", "Johnson Jr.") == "aj johnson"
    assert n.name_key("AJ", "Johnson") == "aj johnson"
    assert n.name_key("Demonte'", "Bolden") == n.name_key("Demonte", "Bolden")
    assert n.name_key("José", "Pérez-Smith") == "jose perez smith"


def test_split_suffix():
    assert n.split_suffix("Johnson Jr.") == ("Johnson", "Jr.")
    assert n.split_suffix("Abernathy IV") == ("Abernathy", "IV")
    assert n.split_suffix("Junior") == ("Junior", None)


def test_numeric_fields():
    assert n.parse_jersey("46") == 46
    assert n.parse_jersey("78/89") is None
    assert n.height_inches(6, 3) == 75
    assert n.height_inches(6, None) == 72
    assert n.height_inches(None, 3) is None
    assert n.parse_weight("311") == 311
    assert n.parse_weight(20) is None


def test_clean_position():
    assert n.clean_position(" QB ") == "QB"
    assert n.clean_position("DE`") == "DE"
    assert n.clean_position("p / pk") == "P/PK"
