from careeros.acquisition.text_extractor import TextExtractor


def test_extractor_normalizes_whitespace() -> None:
    extractor = TextExtractor()
    result = extractor.extract("Hello    World\n\n\nDjango   Developer")
    assert "Hello World" in result
    assert "Django Developer" in result


def test_extractor_removes_excessive_blank_lines() -> None:
    extractor = TextExtractor()
    result = extractor.extract("Line 1\n\n\n\n\nLine 2\n\nLine 3")
    assert result == "Line 1\n\nLine 2\n\nLine 3"


def test_extractor_strips_surrounding_whitespace() -> None:
    extractor = TextExtractor()
    result = extractor.extract("  \n\n  Hello World  \n\n  ")
    assert result == "Hello World"


def test_extractor_handles_empty_input() -> None:
    extractor = TextExtractor()
    assert extractor.extract("") == ""
    assert extractor.extract("   ") == ""
    assert extractor.extract("\n\n\n") == ""
