import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.interview_agent import (  # noqa: E402
    InterviewPracticeAgent,
    EVALUATION_JSON_SCHEMA,
)


class _StubCompletions:
    def __init__(self, log):
        self.log = log

    async def create(self, model, messages, **kwargs):
        self.log.append(messages)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "score": 5,
                                "strengths": [],
                                "weaknesses": [],
                                "improvements": [],
                                "feedback": "",
                                "example_improvement": "",
                                "why_asked": "",
                            }
                        )
                    )
                )
            ]
        )


class _StubClient:
    def __init__(self, log):
        self.chat = SimpleNamespace(completions=_StubCompletions(log))


@pytest.mark.asyncio
async def test_evaluation_prompt_includes_json_schema():
    sent_messages = []
    agent = InterviewPracticeAgent(
        openai_api_key="test",
        openai_model="gpt-4o-mini",
        resume_text="R",
        job_description_text="JD",
        session_id="sess-test",
    )
    agent.client = _StubClient(sent_messages)

    await agent.evaluate_answer("Q1", "A1")

    assert sent_messages, "No messages captured for evaluation request"
    last_request = sent_messages[-1]
    user_msg = next((m for m in last_request if m.get("role") == "user"), {})
    content = user_msg.get("content") or ""
    schema_snippet = json.dumps(EVALUATION_JSON_SCHEMA, indent=2)
    assert schema_snippet in content
    assert "Question type" in content
    assert "STAR + I" in content
    assert "behavioral" in content
