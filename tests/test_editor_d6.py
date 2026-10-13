import pytest
import json
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from app.agents.editor import editor_node
from app.run_health import health

def test_editor_duplicate_category_yields_4_briefs_and_recorded_degradation():
    health.reset()

    # 5 candidates researched
    candidates = [
        {
            "title": f"Project {i}",
            "source": "GitHub",
            "url": f"https://github.com/org/proj{i}",
            "description": f"Project {i} description",
            "content_source": "readme",
            "detailed_content": f"Project {i} detailed content",
            "why_it_matters": "Utility",
            "who_cares": "Developers",
            "verdict": "INTEGRATE"
        }
        for i in range(5)
    ]

    # Model returns 5 briefs, but brief 0 and 1 have duplicate category "Cool Tool"
    duplicate_cat_response = [
        {
            "category": "Cool Tool",
            "title": "Project 0",
            "description": "**Project 0 provides developer tooling.** What happened: Released tooling.",
            "why_it_matters": "Saves time.",
            "who_cares": "Developers.",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/org/proj0"
        },
        {
            "category": "Cool Tool", # Duplicate!
            "title": "Project 1",
            "description": "**Project 1 provides duplicate tooling.** What happened: Released duplicate.",
            "why_it_matters": "Saves time.",
            "who_cares": "Developers.",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/org/proj1"
        },
        {
            "category": "Tech Shift",
            "title": "Project 2",
            "description": "**Project 2 signals industry movement.** What happened: Released architecture.",
            "why_it_matters": "Saves time.",
            "who_cares": "Developers.",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/org/proj2"
        },
        {
            "category": "Career & Learning",
            "title": "Project 3",
            "description": "**Project 3 teaches design patterns.** What happened: Released tutorial.",
            "why_it_matters": "Saves time.",
            "who_cares": "Developers.",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/org/proj3"
        },
        {
            "category": "Ecosystem Update",
            "title": "Project 4",
            "description": "**Project 4 updates major package.** What happened: Released package.",
            "why_it_matters": "Saves time.",
            "who_cares": "Developers.",
            "verdict": "INTEGRATE",
            "source_url": "https://github.com/org/proj4"
        }
    ]

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content=json.dumps(duplicate_cat_response),
        response_metadata={"model_name": "test-mock-model"}
    )

    with patch("app.agents.editor.get_llm", return_value=mock_llm):
        result = editor_node({"vetted_candidates": candidates})

    final_briefs = result["final_briefs"]
    assert len(final_briefs) == 4, f"Expected 4 briefs, got {len(final_briefs)}"
    assert health.has_fallbacks is False, "Duplicate category dropped soft should not cause hard fallback"
    assert health.has_degradations is True
    assert any("Duplicate category 'Cool Tool'" in d["reason"] for d in health.degradations)
