from services.settings_service import normalize_display_name, validate_display_name


def test_normalize_display_name_collapses_spaces() -> None:
    assert normalize_display_name("  А  Б  ") == "А Б"


def test_validate_display_name_ok() -> None:
    name, err = validate_display_name("Герой_12")
    assert err is None
    assert name == "Герой_12"


def test_validate_display_name_too_short() -> None:
    _, err = validate_display_name("Я")
    assert err == "settings_name_short"


def test_validate_rejects_htmlish() -> None:
    _, err = validate_display_name("bad<name>")
    assert err == "settings_name_chars"
