from src.laswitch.heuristics import evaluate_token


def test_en_typed_in_wrong_layout_becomes_ru():
    decision = evaluate_token("Ghbdtn")
    assert decision.should_replace is True
    assert decision.corrected == "Привет"


def test_ru_typed_in_wrong_layout_becomes_en():
    decision = evaluate_token("руддщ")
    assert decision.should_replace is True
    assert decision.corrected == "hello"


def test_normal_english_word_not_replaced():
    decision = evaluate_token("hello")
    assert decision.should_replace is False


def test_normal_russian_word_not_replaced():
    decision = evaluate_token("привет")
    assert decision.should_replace is False