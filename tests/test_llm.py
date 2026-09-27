from pydantic import BaseModel, Field

from core.llm import LLMError, complete_json, extract_json_object


class Toy(BaseModel):
    score: int = Field(ge=0, le=10)
    label: str


def test_extract_json_from_fences():
    blob = extract_json_object('Sure.\n```json\n{"score": 3, "label": "ok"}\n```')
    assert '"score"' in blob


def test_retry_on_malformed_then_success():
    calls = {"n": 0}

    def raw(system, user):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json at all"
        return '{"score": 7, "label": "solid"}'

    out = complete_json("sys", "user", Toy, complete_raw=raw, max_retries=2)
    assert out.score == 7
    assert calls["n"] == 2


def test_validation_retry_out_of_range():
    calls = {"n": 0}

    def raw(system, user):
        calls["n"] += 1
        if calls["n"] == 1:
            return '{"score": 99, "label": "nope"}'
        return '{"score": 2, "label": "fixed"}'

    out = complete_json("s", "u", Toy, complete_raw=raw, max_retries=2)
    assert out.score == 2
    assert calls["n"] == 2


def test_gives_up_after_retries():
    def raw(system, user):
        return "[[[[["

    try:
        complete_json("s", "u", Toy, complete_raw=raw, max_retries=1)
        assert False, "should have raised"
    except LLMError:
        pass
