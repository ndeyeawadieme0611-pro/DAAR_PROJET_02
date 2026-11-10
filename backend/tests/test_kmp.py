import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.search.kmp import carry_over, kmp_contains, kmp_search


# Tables de reports (CarryOver) donnees dans le cours.
@pytest.mark.parametrize(
    "factor, expected",
    [
        ("mami", [-1, 0, -1, 1, 0]),
        ("mamamia", [-1, 0, -1, 0, -1, 3, 0, 0]),
        ("chicha", [-1, 0, 0, -1, 0, 2, 0]),
        ("Sargon", [-1, 0, 0, 0, 0, 0, 0]),
    ],
)
def test_carry_over_cours(factor, expected):
    assert carry_over(factor) == expected


def test_search_cours():
    text = "maman mamé mia ! mm maaah !"
    assert kmp_search(text, "mami") == []
    assert kmp_search(text, "ma") == [0, 2, 6, 20]


def test_search_overlap():
    assert kmp_search("aaaa", "aa") == [0, 1, 2]


def test_search_simple():
    assert kmp_search("abracadabra", "abra") == [0, 7]
    assert kmp_search("abracadabra", "cad") == [4]
    assert kmp_search("abc", "abcd") == []


def test_empty_factor():
    assert kmp_search("abc", "") == []


def test_contains():
    assert kmp_contains("the quick brown fox", "brown")
    assert not kmp_contains("the quick brown fox", "cat")


def test_matches_naive_on_random():
    import random

    rnd = random.Random(0)
    for _ in range(300):
        text = "".join(rnd.choice("ab") for _ in range(rnd.randint(0, 40)))
        f = "".join(rnd.choice("ab") for _ in range(rnd.randint(1, 5)))
        naive = [i for i in range(len(text) - len(f) + 1) if text[i : i + len(f)] == f]
        assert kmp_search(text, f) == naive
