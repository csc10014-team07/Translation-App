"""
Evaluation metrics calculation module.

Provides deterministic implementations for:
- WER (Word Error Rate)
- CER (Character Error Rate)
- BLEU (sentence and corpus level, with brevity penalty)
- chrF / chrF++ (Character n-gram F-score)
- Context & Pronoun Match Rate (for context presets)

The local implementations are used unconditionally so results do not change
depending on whether optional metric packages are installed.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import Any


def _levenshtein_distance(seq1: Sequence[Any], seq2: Sequence[Any]) -> int:
    """Compute standard Levenshtein edit distance between two sequences."""
    n1, n2 = len(seq1), len(seq2)
    if n1 == 0:
        return n2
    if n2 == 0:
        return n1

    prev_row = list(range(n2 + 1))
    for i in range(1, n1 + 1):
        curr_row = [i] + [0] * n2
        for j in range(1, n2 + 1):
            cost = 0 if seq1[i - 1] == seq2[j - 1] else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,       # insertion
                prev_row[j] + 1,           # deletion
                prev_row[j - 1] + cost,    # substitution
            )
        prev_row = curr_row

    return prev_row[n2]


def normalize_text_for_eval(text: str) -> str:
    """Normalize text for fair metric evaluation (lowercase, strip extra spaces, punctuation)."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\d]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _contains_keyword(text: str, keyword: str) -> bool:
    """Match a keyword as a whole word/phrase using Unicode-aware boundaries."""
    needle = keyword.strip()
    if not needle:
        return False
    pattern = r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def calculate_wer(reference: str, hypothesis: str, normalize: bool = True) -> float:
    """
    Calculate Word Error Rate (WER) = (S + D + I) / N_ref.
    Returns float between 0.0 and infinity (usually <= 1.0, formatted as percentage in reports).
    """
    if normalize:
        ref_words = normalize_text_for_eval(reference).split()
        hyp_words = normalize_text_for_eval(hypothesis).split()
    else:
        ref_words = reference.strip().split()
        hyp_words = hypothesis.strip().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    distance = _levenshtein_distance(ref_words, hyp_words)
    return float(distance / len(ref_words))


def calculate_cer(reference: str, hypothesis: str, normalize: bool = True) -> float:
    """
    Calculate Character Error Rate (CER) = (S + D + I) / N_ref_chars.
    Returns float between 0.0 and infinity.
    """
    if normalize:
        ref_chars = list(normalize_text_for_eval(reference))
        hyp_chars = list(normalize_text_for_eval(hypothesis))
    else:
        ref_chars = list(reference.strip())
        hyp_chars = list(hypothesis.strip())

    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    distance = _levenshtein_distance(ref_chars, hyp_chars)
    return float(distance / len(ref_chars))


def _extract_ngrams(tokens: list[str], n: int) -> Counter[tuple[str, ...]]:
    """Extract token n-grams and return their frequency counts."""
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def calculate_sentence_bleu(
    reference: str,
    hypothesis: str,
    max_order: int = 4,
    smooth: bool = True,
) -> float:
    """
    Calculate sentence-level BLEU score (0.0 to 100.0) with brevity penalty.

    The effective n-gram order is capped by the shorter sentence, so a perfect
    short sentence is not forced to score 0 because it has no 4-grams.
    """
    ref_tokens = normalize_text_for_eval(reference).split()
    hyp_tokens = normalize_text_for_eval(hypothesis).split()

    hyp_len = len(hyp_tokens)
    ref_len = len(ref_tokens)

    if hyp_len == 0 or ref_len == 0:
        return 0.0

    effective_order = min(max_order, hyp_len, ref_len)
    if effective_order == 0:
        return 0.0

    # Brevity penalty
    if hyp_len > ref_len:
        bp = 1.0
    else:
        bp = math.exp(1.0 - (ref_len / hyp_len))

    precisions: list[float] = []
    for order in range(1, effective_order + 1):
        hyp_ngrams = _extract_ngrams(hyp_tokens, order)
        ref_ngrams = _extract_ngrams(ref_tokens, order)

        possible_matches = sum(hyp_ngrams.values())
        clipped_matches = sum(
            min(count, ref_ngrams.get(ngram, 0)) for ngram, count in hyp_ngrams.items()
        )

        if clipped_matches == 0:
            precisions.append(0.1 / possible_matches if smooth else 0.0)
        else:
            precisions.append(clipped_matches / possible_matches)

    # Geometric mean
    if any(p <= 0.0 for p in precisions):
        return 0.0

    geo_mean = math.exp(sum(math.log(p) for p in precisions) / len(precisions))
    return float(bp * geo_mean * 100.0)


def calculate_corpus_bleu(
    references: list[str],
    hypotheses: list[str],
    max_order: int = 4,
    smooth: bool = True,
) -> float:
    """Calculate corpus-level BLEU by aggregating n-gram counts across sentences."""
    if not references or len(references) != len(hypotheses):
        return 0.0

    matches = [0] * max_order
    possible = [0] * max_order
    hyp_len = 0
    ref_len = 0

    for reference, hypothesis in zip(references, hypotheses, strict=True):
        ref_tokens = normalize_text_for_eval(reference).split()
        hyp_tokens = normalize_text_for_eval(hypothesis).split()
        hyp_len += len(hyp_tokens)
        ref_len += len(ref_tokens)

        for order in range(1, max_order + 1):
            hyp_ngrams = _extract_ngrams(hyp_tokens, order)
            ref_ngrams = _extract_ngrams(ref_tokens, order)
            possible[order - 1] += sum(hyp_ngrams.values())
            matches[order - 1] += sum(
                min(count, ref_ngrams.get(ngram, 0)) for ngram, count in hyp_ngrams.items()
            )

    if hyp_len == 0 or ref_len == 0:
        return 0.0

    if hyp_len > ref_len:
        bp = 1.0
    else:
        bp = math.exp(1.0 - (ref_len / hyp_len))

    precisions: list[float] = []
    for matched, total in zip(matches, possible, strict=True):
        if total == 0:
            break
        precisions.append(0.1 / total if matched == 0 and smooth else matched / total)

    if not precisions or any(p <= 0.0 for p in precisions):
        return 0.0

    geo_mean = math.exp(sum(math.log(p) for p in precisions) / len(precisions))
    return float(bp * geo_mean * 100.0)


def calculate_sentence_chrf(
    reference: str,
    hypothesis: str,
    char_order: int = 6,
    word_order: int = 2,
    beta: float = 2.0,
) -> float:
    """
    Calculate sentence-level chrF++ score (character n-grams + word n-grams F-score).
    Standard metric for morphologically rich languages like Vietnamese.
    """
    ref_str = re.sub(r"\s+", " ", reference.strip())
    hyp_str = re.sub(r"\s+", " ", hypothesis.strip())

    if not hyp_str:
        return 0.0
    if not ref_str:
        return 0.0

    total_f = 0.0
    count_orders = 0
    beta_sq = beta**2

    def _accumulate(hyp_ngrams: Counter[Any], ref_ngrams: Counter[Any]) -> None:
        nonlocal total_f, count_orders
        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())
        if hyp_total == 0 or ref_total == 0:
            return

        matched = sum(min(c, ref_ngrams.get(ng, 0)) for ng, c in hyp_ngrams.items())
        prec = matched / hyp_total
        rec = matched / ref_total
        denom = beta_sq * prec + rec
        total_f += (1 + beta_sq) * prec * rec / denom if denom > 0 else 0.0
        count_orders += 1

    # Character n-grams
    for n in range(1, char_order + 1):
        hyp_c_ngrams = Counter(hyp_str[i : i + n] for i in range(len(hyp_str) - n + 1))
        ref_c_ngrams = Counter(ref_str[i : i + n] for i in range(len(ref_str) - n + 1))
        _accumulate(hyp_c_ngrams, ref_c_ngrams)

    # Word n-grams (chrF++ component)
    if word_order > 0:
        hyp_words = hyp_str.split()
        ref_words = ref_str.split()
        for n in range(1, word_order + 1):
            _accumulate(_extract_ngrams(hyp_words, n), _extract_ngrams(ref_words, n))

    return float((total_f / count_orders * 100.0) if count_orders > 0 else 0.0)


def evaluate_context_preset_sample(
    preset: str,
    hypothesis: str,
    required_keywords: list[str] | None = None,
    forbidden_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """
    Evaluate whether a model hypothesis respects a context preset (e.g. Formal, Friendly, IT).

    Required keywords are treated as alternatives from the curated dataset: at
    least one must appear. Forbidden keywords must not appear. Matching uses
    whole-word boundaries so a keyword is not detected inside a longer token.

    Returns:
        dict with keys:
        - passed: bool
        - found_required: list of matched required keywords
        - found_forbidden: list of matched forbidden keywords
        - required_coverage: float (fraction of required keywords present)
        - score: float (required coverage, or 0.0 when forbidden words are found)
    """
    hyp = hypothesis.strip()
    req = required_keywords or []
    forb = forbidden_keywords or []

    if not hyp:
        return {
            "preset": preset,
            "passed": False,
            "score": 0.0,
            "required_coverage": 0.0,
            "found_required": [],
            "found_forbidden": [],
        }

    found_required = [kw for kw in req if _contains_keyword(hyp, kw)]
    found_forbidden = [kw for kw in forb if _contains_keyword(hyp, kw)]

    required_total = len(req)
    required_coverage = (len(found_required) / required_total) if required_total else 1.0
    has_required = required_total == 0 or len(found_required) > 0
    has_no_forbidden = len(found_forbidden) == 0

    passed = has_required and has_no_forbidden
    score = required_coverage if passed else 0.0

    return {
        "preset": preset,
        "passed": passed,
        "score": score,
        "required_coverage": required_coverage,
        "found_required": found_required,
        "found_forbidden": found_forbidden,
    }
