"""Text normalization utilities for speech synthesis and ASR datasets."""
from __future__ import annotations

import re
from typing import Iterable, Mapping

DIGIT_MAP = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

ORDINAL_MAP = {
    "1": "first",
    "2": "second",
    "3": "third",
    "4": "fourth",
    "5": "fifth",
    "6": "sixth",
    "7": "seventh",
    "8": "eighth",
    "9": "ninth",
    "10": "tenth",
    "11": "eleventh",
    "12": "twelfth",
}

ABBREVIATIONS = {
    "mr.": "mister",
    "mrs.": "misses",
    "dr.": "doctor",
    "st.": "street",
    "ave.": "avenue",
    "jan.": "january",
    "feb.": "february",
    "mar.": "march",
    "apr.": "april",
    "jun.": "june",
    "jul.": "july",
    "aug.": "august",
    "sep.": "september",
    "sept.": "september",
    "oct.": "october",
    "nov.": "november",
    "dec.": "december",
}

MULTISPACE_PATTERN = re.compile(r"\s+")
NUMBER_PATTERN = re.compile(r"(\d+)(st|nd|rd|th)?")
MONEY_PATTERN = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")
PERCENT_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)%")


def _expand_ordinal(match: re.Match[str]) -> str:
    number, suffix = match.groups()
    if suffix:
        if number in ORDINAL_MAP:
            return ORDINAL_MAP[number]
        return f"{_spell_number(number)} {suffix[:-2]}"
    return _spell_number(number)


def _spell_number(number: str) -> str:
    if len(number) > 3:
        # Fallback to simple digit reading for long numbers
        return " ".join(DIGIT_MAP.get(d, d) for d in number)
    try:
        return {
            0: "zero",
            1: "one",
            2: "two",
            3: "three",
            4: "four",
            5: "five",
            6: "six",
            7: "seven",
            8: "eight",
            9: "nine",
            10: "ten",
            11: "eleven",
            12: "twelve",
            13: "thirteen",
            14: "fourteen",
            15: "fifteen",
            16: "sixteen",
            17: "seventeen",
            18: "eighteen",
            19: "nineteen",
            20: "twenty",
        }[int(number)]
    except (KeyError, ValueError):
        return " ".join(DIGIT_MAP.get(d, d) for d in number)


def expand_numbers(text: str) -> str:
    """Convert numeric expressions to a speakable form."""

    def replace(match: re.Match[str]) -> str:
        return _expand_ordinal(match)

    text = MONEY_PATTERN.sub(lambda m: f"{m.group(1)} dollars", text)
    text = PERCENT_PATTERN.sub(lambda m: f"{m.group(1)} percent", text)
    text = NUMBER_PATTERN.sub(replace, text)
    return text


def expand_abbreviations(text: str, mapping: Mapping[str, str] | None = None) -> str:
    """Expand known abbreviations in the provided text."""
    mapping = mapping or ABBREVIATIONS
    words = []
    for token in text.split():
        lower = token.lower()
        replacement = mapping.get(lower)
        if replacement:
            words.append(replacement)
        else:
            words.append(token)
    return " ".join(words)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u3000", " ")  # full-width space
    text = MULTISPACE_PATTERN.sub(" ", text)
    return text.strip()


def normalize_text(text: str, extra_abbreviations: Mapping[str, str] | None = None) -> str:
    """Normalize the input text for speech datasets.

    The normalization pipeline performs the following:

    * Unicode whitespace cleanup
    * Lower-casing
    * Abbreviation expansion (with optional custom entries)
    * Number, percentage, and currency expansion
    * Removal of extraneous punctuation often found in transcripts
    """

    if not text:
        return ""
    text = text.lower()
    text = normalize_whitespace(text)
    text = expand_abbreviations(text, extra_abbreviations)
    text = expand_numbers(text)
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201c\u201d]", '"', text)
    text = re.sub(r"[^a-z0-9'\s.,?!]", " ", text)
    text = normalize_whitespace(text)
    return text


def batch_normalize_text(texts: Iterable[str]) -> Iterable[str]:
    """Normalize an iterable of strings lazily."""
    for text in texts:
        yield normalize_text(text)
