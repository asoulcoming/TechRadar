"""Basic sentiment analysis — placeholder for future LLM-based implementation."""

import re


# Simple keyword-based sentiment (placeholder until LLM integration)
POSITIVE_WORDS = [
    "好用", "推荐", "神器", "优秀", "牛逼", "牛逼", "强大", "实用", "高效",
    "必备", "精华", "干货", "赞", "简洁", "优雅", "好评",
    "great", "excellent", "awesome", "best", "amazing", "love",
]
NEGATIVE_WORDS = [
    "难用", "垃圾", "坑", "踩坑", "差评", "失望", "烂", "复杂", "繁琐",
    "bug", "问题", "不行", "劝退",
    "bad", "terrible", "worst", "hate", "ugly",
]


def analyze_sentiment(text: str) -> dict:
    """Simple rule-based sentiment analysis.

    Returns: {"label": "positive"|"negative"|"neutral", "score": float in [-1, 1]}
    """
    if not text:
        return {"label": "neutral", "score": 0.0}

    text_lower = text.lower()
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

    total = pos_count + neg_count
    if total == 0:
        return {"label": "neutral", "score": 0.0}

    score = (pos_count - neg_count) / max(total, 1)
    score = max(-1.0, min(1.0, score))

    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"

    return {"label": label, "score": score}
