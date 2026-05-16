from mtgdeck.rules.color_identity import (
    is_within_color_identity,
    format_color_identity,
    color_identity_name,
)


def test_mono_black_within_mono_black():
    assert is_within_color_identity(["B"], ["B"])


def test_mono_black_outside_mono_green():
    assert not is_within_color_identity(["B"], ["G"])


def test_colorless_within_any():
    assert is_within_color_identity([], ["B", "G"])
    assert is_within_color_identity(["C"], ["W"])
    assert is_within_color_identity([], [])


def test_two_color_within_five_color():
    assert is_within_color_identity(["U", "B"], ["W", "U", "B", "R", "G"])


def test_two_color_outside_mono():
    assert not is_within_color_identity(["U", "B"], ["U"])


def test_format_color_identity_wubrg_order():
    assert format_color_identity(["G", "W", "B", "R", "U"]) == "WUBRG"


def test_format_color_identity_empty_is_C():
    assert format_color_identity([]) == "C"


def test_color_identity_name_mono():
    assert color_identity_name(["B"]) == "Black"


def test_color_identity_name_multicolor():
    assert color_identity_name(["W", "U"]) == "White/Blue"


def test_color_identity_name_colorless():
    assert color_identity_name([]) == "Colorless"
    assert color_identity_name(["C"]) == "Colorless"
