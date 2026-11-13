import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from app.regex.engine import build_matcher

CASES = [
    ("S(a|g|r)+on", ["Sargon", "Saon", "Sion", "Sargonx", "Son"]),
    ("lo.e", ["love", "lovee", "lve", "lote"]),
    ("ab*", ["a", "ab", "abbb", "b", ""]),
    ("(ab)*", ["", "ab", "abab", "aba"]),
    ("chat|chien", ["chat", "chien", "chaen"]),
]

@pytest.mark.parametrize("pattern,words", CASES)
def test_same_as_python_re(pattern, words):
    m = build_matcher(pattern)
    for w in words:
        assert m(w) == (re.fullmatch(pattern, w) is not None), (pattern, w)

@pytest.mark.parametrize("bad", ["(ab", "*a", "a|", ")"])
def test_invalid_raises_value_error(bad):
    with pytest.raises(ValueError):
        build_matcher(bad)
