from pydantic import BaseModel, Field

from core.grounding import collect_source_ids, ground_model
from core.store import EvidenceStore


class Claim(BaseModel):
    source_id: str
    source_ids: list[str] = Field(default_factory=list)
    text: str = ""


class Bundle(BaseModel):
    claims: list[Claim]


def _store() -> EvidenceStore:
    store = EvidenceStore()
    store.ingest_search(
        "google_scholar",
        {
            "organic_results": [
                {
                    "title": "Real paper",
                    "link": "https://arxiv.org/abs/1",
                    "snippet": "exists",
                    "year": "2021",
                }
            ]
        },
        "q",
    )
    return store


def test_drops_unknown_ids_keeps_real_ones():
    store = _store()
    raw = Bundle(
        claims=[
            Claim(source_id="SRC-001", source_ids=["SRC-001", "SRC-999"], text="ok"),
            Claim(source_id="SRC-404", source_ids=["SRC-404"], text="invented"),
        ]
    )
    cleaned, dropped = ground_model(raw, store)
    assert "SRC-999" in dropped and "SRC-404" in dropped
    assert cleaned.claims[0].source_id == "SRC-001"
    assert cleaned.claims[0].source_ids == ["SRC-001"]
    assert cleaned.claims[1].source_id == ""
    assert cleaned.claims[1].source_ids == []


def test_collect_source_ids():
    raw = Claim(source_id="SRC-001", source_ids=["SRC-002"])
    ids = collect_source_ids(raw)
    assert "SRC-001" in ids and "SRC-002" in ids
