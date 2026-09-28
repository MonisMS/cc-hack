from pydantic import BaseModel

from app.core import llm
from app.core.config import settings


def test_guard_rejects_hardcoded_numbers():
    assert llm._guard({"sentence": "grew by 12%"}, {"delta": "+12"}) is False


def test_guard_accepts_placeholder_tokens():
    assert llm._guard({"sentence": "grew by {delta}%"}, {"delta": "+12"}) is True


def test_guard_rejects_unknown_placeholder():
    assert llm._guard({"sentence": "grew by {mystery}%"}, {"delta": "+12"}) is False


class _Sentence(BaseModel):
    sentence: str


def test_generate_text_returns_template_with_no_keys(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "cerebras_api_key", None)

    template = _Sentence(sentence="At the site, cover changed by +5 points.")
    result, model_used = llm.generate_text(
        task="change_description_test",
        prompt="irrelevant",
        placeholders={"delta": "+5"},
        schema=_Sentence,
        template=template,
    )
    assert model_used == "template"
    assert result is template
