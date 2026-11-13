import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ranker import Ranker, stem, tokens

from fixes.common.data import catalog_items

ITEMS = catalog_items()


def ids(r, q, k=3):
    return [i["locator"]["solutionId"] for i in r.search(q, k)]


def test_tokens_drop_stopwords_and_stem():
    assert tokens("Find the investors for my round") == ["find", "investor", "round"]
    assert stem("battlecards") == "battlecard"


def test_missing_word_does_not_zero_results():
    r = Ranker(ITEMS)
    assert ids(r, "investors xylophone")[0] == "investor-match"


def test_unknown_query_returns_empty():
    assert Ranker(ITEMS).search("xylophone qwertyuiop") == []


def test_keyword_queries_still_work():
    r = Ranker(ITEMS)
    assert ids(r, "battlecard")[0] == "competitor-battlecards"
    assert ids(r, "new YC founders")[0] == "yc-new-founder-early-finder"


def test_name_outweighs_description():
    items = [
        {"locator": {"solutionId": "a"}, "name": "Lead Finder", "description": "x"},
        {
            "locator": {"solutionId": "b"},
            "name": "Other",
            "description": "lead finder lead",
        },
    ]
    assert ids(Ranker(items), "lead finder", 1) == ["a"]


def test_plain_bm25_meets_top3_target_on_eval_set():
    queries = json.loads((Path(__file__).parent / "queries.json").read_text())
    r = Ranker(ITEMS)
    hits = sum(any(i in q["relevant"] for i in ids(r, q["q"])) for q in queries)
    assert hits >= 19
