import pytest
import spacy

from nlp.extract_rules import Extractor, classify_severity


@pytest.fixture(scope="module")
def extractor():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return Extractor({"aspirin": "aspirin", "warfarin": "warfarin", "coumadin": "warfarin"},
                     {"peptic ulcer": "peptic ulcer"}, nlp)


@pytest.mark.parametrize(("text", "kind", "expected"), [
    ("Concomitant use with WARFARIN is contraindicated.", "interaction", [("warfarin", "MAJOR", .9)]),
    ("Monitor closely when taking Coumadin.", "interaction", [("warfarin", "MODERATE", .9)]),
    ("A minor effect was observed with warfarin.", "interaction", [("warfarin", "MINOR", .9)]),
    ("Warfarin changes absorption.", "interaction", [("warfarin", "MODERATE", .6)]),
    ("Avoid aspirin in peptic ulcer.", "contraindication", [("peptic ulcer", "MAJOR", .9)]),
    ("Aspirin is contraindicated. Nonwarfarin is separate.", "interaction", []),
])
def test_sentence(extractor, text, kind, expected):
    assert extractor.predict(text, "aspirin", kind) == expected


def test_severity_priority_and_word_boundaries():
    assert classify_severity("Monitor for severe reactions.") == ("MAJOR", .9)
    assert classify_severity("A smaller amount was studied.") == ("MODERATE", .6)


def test_evaluation_counts_severity_errors_and_missed_pairs():
    from nlp.evaluate import evaluate

    first = ("label", "aspirin", "Sentence.", "interaction", "warfarin")
    second = ("label", "aspirin", "Other sentence.", "contraindication", "peptic ulcer")
    report = evaluate({(*first, "MODERATE")}, {(*first, "MAJOR"), (*second, "MINOR")})
    assert report["pair_or_condition"]["precision"] == 1
    assert report["pair_or_condition"]["recall"] == .5
    assert report["pair_or_condition"]["f1"] == pytest.approx(2 / 3)
    assert report["with_severity"]["f1"] == 0
    assert report["severity_confusion"]["MAJOR"]["MODERATE"] == 1
    assert report["severity_confusion"]["MINOR"]["MISSING"] == 1
