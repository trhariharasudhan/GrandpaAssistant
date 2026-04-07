from __future__ import annotations

from functools import lru_cache

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:  # pragma: no cover - fallback path for missing optional dependency
    SentimentIntensityAnalyzer = None


ANGER_CUES = (
    "angry",
    "mad",
    "frustrated",
    "furious",
    "annoyed",
    "irritated",
    "pissed",
    "hate",
    "fed up",
    "sick of",
)

SAD_CUES = (
    "sad",
    "feeling low",
    "low",
    "down",
    "upset",
    "hurt",
    "depressed",
    "lonely",
    "crying",
    "miserable",
)

EMOTION_TONE_INSTRUCTIONS = {
    "happy": "Be cheerful and match the user's positive energy.",
    "sad": "Be empathetic, supportive, and comforting.",
    "angry": "Stay calm, polite, and help de-escalate the situation.",
    "neutral": "Be friendly and neutral.",
}


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer | None:
    if SentimentIntensityAnalyzer is None:
        return None
    return SentimentIntensityAnalyzer()


def _normalized_text(text: str | None) -> str:
    return " ".join(str(text or "").strip().split())


def _has_anger_cue(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ANGER_CUES)


def _has_sad_cue(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in SAD_CUES)


def emotion_instruction(emotion: str | None) -> str:
    return EMOTION_TONE_INSTRUCTIONS.get(str(emotion or "neutral").strip().lower(), EMOTION_TONE_INSTRUCTIONS["neutral"])


def analyze_emotion(text: str | None) -> dict:
    normalized = _normalized_text(text)
    if not normalized:
        return {
            "emotion": "neutral",
            "compound": 0.0,
            "instruction": emotion_instruction("neutral"),
            "scores": {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0},
        }

    analyzer = _analyzer()
    if analyzer is None:
        compound = 0.0
        scores = {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    else:
        scores = analyzer.polarity_scores(normalized)
        compound = float(scores.get("compound", 0.0))

    if compound >= 0.5:
        emotion = "happy"
    elif _has_anger_cue(normalized) and compound < -0.2:
        emotion = "angry"
    elif _has_sad_cue(normalized) and compound < -0.1:
        emotion = "sad"
    elif compound <= -0.5:
        emotion = "sad"
    elif compound < -0.2:
        emotion = "angry"
    else:
        emotion = "neutral"

    return {
        "emotion": emotion,
        "compound": round(compound, 4),
        "instruction": emotion_instruction(emotion),
        "scores": {
            "neg": round(float(scores.get("neg", 0.0)), 4),
            "neu": round(float(scores.get("neu", 0.0)), 4),
            "pos": round(float(scores.get("pos", 0.0)), 4),
            "compound": round(float(scores.get("compound", 0.0)), 4),
        },
    }


def detect_emotion(text: str | None) -> str:
    return analyze_emotion(text)["emotion"]


def build_emotion_prompt_context(text: str | None) -> str:
    analysis = analyze_emotion(text)
    return (
        f"Detected user emotion: {analysis['emotion']}.\n"
        f"Emotion response guidance: {analysis['instruction']}"
    )
