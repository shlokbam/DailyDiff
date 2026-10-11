from deepeval.metrics import GEval
try:
    from deepeval.test_case import SingleTurnParams as EvaluationParams
except ImportError:
    from deepeval.test_case import LLMTestCaseParams as EvaluationParams

def create_skeptic_geval(judge=None, threshold: float = 0.7) -> GEval:
    """G-Eval metric assessing whether Skeptic candidate signals align with student/developer utility."""
    return GEval(
        name="Skeptic Relevance & Noise Filtering",
        criteria=(
            "Evaluate whether the technical candidate signal is substantial, educational, and high-value "
            "for tech students and early-career software developers (e.g. coding guides, open-source utilities, "
            "developer frameworks, portfolio tools), while strictly rejecting dense enterprise-only infrastructure "
            "and incremental version duplicates."
        ),
        evaluation_params=[EvaluationParams.INPUT, EvaluationParams.ACTUAL_OUTPUT, EvaluationParams.EXPECTED_OUTPUT],
        model=judge,
        threshold=threshold
    )

def create_verifier_geval(judge=None, threshold: float = 0.7) -> GEval:
    """G-Eval metric assessing technical factuality and groundedness against reference documentation."""
    return GEval(
        name="Verifier Groundedness & Anti-Hype",
        criteria=(
            "Evaluate whether the candidate claims and descriptions are factually substantiated by the reference "
            "documentation without hallucination, marketing exaggeration, false claims, or empty placeholder repos."
        ),
        evaluation_params=[EvaluationParams.INPUT, EvaluationParams.ACTUAL_OUTPUT, EvaluationParams.CONTEXT],
        model=judge,
        threshold=threshold
    )

def create_analyst_practicality_geval(judge=None, threshold: float = 0.7) -> GEval:
    """G-Eval metric assessing pedagogical practicality and actionable takeaways for developers."""
    return GEval(
        name="Analyst Pedagogical Practicality",
        criteria=(
            "Assess whether the 'why_it_matters' takeaway conveys actionable engineering value: "
            "explaining what developers can build, learn, save, or debug, using concrete action verbs "
            "rather than superficial marketing summaries."
        ),
        evaluation_params=[EvaluationParams.INPUT, EvaluationParams.ACTUAL_OUTPUT, EvaluationParams.EXPECTED_OUTPUT],
        model=judge,
        threshold=threshold
    )

def create_analyst_audience_geval(judge=None, threshold: float = 0.7) -> GEval:
    """G-Eval metric assessing audience role precision."""
    return GEval(
        name="Analyst Audience Specificity",
        criteria=(
            "Assess whether the identified target audience specifically designates relevant student roles, "
            "beginner developers, or specialty tracks (e.g. CS students building portfolios, React beginners) "
            "rather than broad non-specific labels."
        ),
        evaluation_params=[EvaluationParams.ACTUAL_OUTPUT, EvaluationParams.EXPECTED_OUTPUT],
        model=judge,
        threshold=threshold
    )

def create_editor_readability_geval(judge=None, threshold: float = 0.7) -> GEval:
    """G-Eval metric assessing ELI5 tone and conversational clarity."""
    return GEval(
        name="Editor ELI5 Readability & Tone",
        criteria=(
            "Assess whether the briefing text adopts a crisp, conversational, developer-friendly ELI5 tone "
            "(explaining concepts simply without complex academic theory), starts with a bold summary sentence, "
            "and eliminates forbidden labels such as 'TL;DR:'."
        ),
        evaluation_params=[EvaluationParams.INPUT, EvaluationParams.ACTUAL_OUTPUT],
        model=judge,
        threshold=threshold
    )
