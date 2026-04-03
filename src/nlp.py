from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List

try:
    import spacy
except Exception:
    spacy = None  # type: ignore

try:
    from textblob import TextBlob
except Exception:
    TextBlob = None  # type: ignore

try:
    from transformers import T5ForConditionalGeneration, T5Tokenizer
except Exception:
    T5ForConditionalGeneration = None  # type: ignore
    T5Tokenizer = None  # type: ignore


MONEY_REGEX = re.compile(
    r"(?:\u20B9|\$|EUR|INR|USD)\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:rupees|dollars|usd|inr)\b",
    flags=re.IGNORECASE,
)
MIN_SUMMARY_INPUT = 1500
MAX_SUMMARY_INPUT = 2000


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip(" \n\t,.;:")


def _is_valid_entity(value: str) -> bool:
    if not value:
        return False
    if len(value) < 2:
        return False
    return bool(re.search(r"[A-Za-z0-9]", value))


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for value in values:
        cleaned = _clean_value(value)
        key = cleaned.casefold()
        if _is_valid_entity(cleaned) and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def _load_spacy_model():
    if spacy is None:
        return None
    try:
        return spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer", "textcat"])
    except Exception:
        return spacy.blank("en")


def _load_t5():
    if T5Tokenizer is None or T5ForConditionalGeneration is None:
        return None, None
    try:
        tokenizer = T5Tokenizer.from_pretrained("t5-small", local_files_only=True)
        model = T5ForConditionalGeneration.from_pretrained("t5-small", local_files_only=True)
        return tokenizer, model
    except Exception:
        return None, None


NLP = _load_spacy_model()
T5_TOKENIZER = None
T5_MODEL = None
T5_LOAD_ATTEMPTED = False


@lru_cache(maxsize=128)
def _extract_entities_cached(cleaned_text: str):
    names: List[str] = []
    dates: List[str] = []
    organizations: List[str] = []
    amounts: List[str] = []

    if cleaned_text:
        doc = NLP(cleaned_text) if NLP is not None else None
        for ent in getattr(doc, "ents", []) if doc is not None else []:
            label = ent.label_
            value = ent.text
            if label == "PERSON":
                names.append(value)
            elif label == "DATE":
                dates.append(value)
            elif label == "ORG":
                organizations.append(value)
            elif label == "MONEY":
                amounts.append(value)

        amounts.extend(MONEY_REGEX.findall(cleaned_text))

    return (
        tuple(_dedupe(names)),
        tuple(_dedupe(dates)),
        tuple(_dedupe(organizations)),
        tuple(_dedupe(amounts)),
    )


def get_entities(text: str) -> Dict[str, List[str]]:
    cleaned_text = _clean_value(text)
    names, dates, organizations, amounts = _extract_entities_cached(cleaned_text)
    return {
        "names": list(names),
        "dates": list(dates),
        "organizations": list(organizations),
        "amounts": list(amounts),
    }


@lru_cache(maxsize=128)
def _summary_fallback_cached(chunk: str) -> str:
    return chunk[:280]


def get_summary(text: str) -> str:
    global T5_TOKENIZER, T5_MODEL, T5_LOAD_ATTEMPTED
    cleaned_text = _clean_value(text)
    if not cleaned_text:
        return ""

    target_chars = MAX_SUMMARY_INPUT if len(cleaned_text) >= MAX_SUMMARY_INPUT else MIN_SUMMARY_INPUT
    chunk = cleaned_text[:target_chars]

    if not T5_LOAD_ATTEMPTED:
        T5_TOKENIZER, T5_MODEL = _load_t5()
        T5_LOAD_ATTEMPTED = True

    if T5_TOKENIZER is None or T5_MODEL is None:
        return _summary_fallback_cached(chunk)

    try:
        prompt = f"summarize: {chunk}"
        inputs = T5_TOKENIZER(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        summary_ids = T5_MODEL.generate(
            **inputs,
            max_length=64,
            min_length=16,
            length_penalty=1.2,
            num_beams=1,
            early_stopping=True,
        )
        summary = T5_TOKENIZER.decode(summary_ids[0], skip_special_tokens=True)
        return _clean_value(summary)[:300]
    except Exception:
        return _summary_fallback_cached(chunk)


@lru_cache(maxsize=256)
def _sentiment_cached(cleaned_text: str) -> str:
    if not cleaned_text or TextBlob is None:
        return "Neutral"
    polarity = TextBlob(cleaned_text[:2500]).sentiment.polarity
    if polarity > 0.1:
        return "Positive"
    if polarity < -0.1:
        return "Negative"
    return "Neutral"


def get_sentiment(text: str) -> str:
    cleaned_text = _clean_value(text)
    try:
        sentiment = _sentiment_cached(cleaned_text)
        return sentiment if sentiment in {"Positive", "Neutral", "Negative"} else "Neutral"
    except Exception:
        return "Neutral"
