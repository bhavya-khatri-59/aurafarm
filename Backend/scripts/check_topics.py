"""Shows how the optional embedding topic filter scores messages, to tune TOPIC_FILTER_MARGIN.

Usage (from Backend/):  python -m scripts.check_topics ["your message" ...]
Without arguments it scores a built-in mix of farming and off-topic messages.
"""

import sys

from app.config import get_settings
from app.services.topic_filter import MIN_WORDS, topic_scores_sync

SAMPLES = [
    "How do I stop late blight spreading to my other tomato plants?",
    "Is it safe to spray copper fungicide if it will rain tomorrow?",
    "My maize leaves have brown streaks, what could it be?",
    "Which fertilizer should I use for potatoes in sandy soil?",
    "Where can I buy neem oil near me?",
    "Can you help me write a cover letter for a job?",
    "Who won the cricket match yesterday?",
    "Explain quantum computing in simple terms",
    "Give me a recipe for chocolate cake",
    "Write a short story about a dragon",
]


def main(messages: list[str]) -> None:
    margin = get_settings().topic_filter_margin
    for message in messages or SAMPLES:
        if len(message.split()) < MIN_WORDS:
            print(f"   (short, always allowed)          {message}")
            continue
        on_topic, off_topic = topic_scores_sync(message)
        verdict = "BLOCK" if off_topic - on_topic > margin else "allow"
        print(f"on={on_topic:.3f} off={off_topic:.3f} diff={off_topic - on_topic:+.3f}  {verdict}  {message}")
    print(f"\nBlocked when off - on > {margin} (TOPIC_FILTER_MARGIN)")


if __name__ == "__main__":
    main(sys.argv[1:])
