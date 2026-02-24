from typing import List, Optional
from nlp.scoring import DEFAULT_KEYWORDS

def start_interview(candidate_text: Optional[str] = None) -> List[str]:
    """Generate suggested interview questions.
    If `candidate_text` is provided, prioritize skills found in text.
    """
    base = [
        "Tell me about yourself",
        "What are your technical skills?",
        "Why should we hire you?",
        "Describe a project you worked on"
    ]
    if not candidate_text:
        return base

    words = set(candidate_text.lower().split())
    skills = [k for k in DEFAULT_KEYWORDS if k in words]
    questions = [f"Tell me about your experience with {s}." for s in skills]
    # ensure at least some base questions
    return questions + base
