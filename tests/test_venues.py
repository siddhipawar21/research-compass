from core.store import EvidenceStore
from modules.venues import extract_deadline, heuristic_venues


def test_deadline_extracted_when_present():
    assert extract_deadline("Paper deadline 12 Feb 2026. Extra text") != "not found"
    assert "2026" in extract_deadline("Application due 30 Sep 2026")


def test_deadline_not_invented_from_random_year():
    assert extract_deadline("Work published in 2022 on graphs") == "not found"


def test_venues_mark_not_found():
    store = EvidenceStore()
    store.ingest_search(
        "google",
        {
            "organic_results": [
                {
                    "title": "SERB Core Research Grant India",
                    "link": "https://serb.gov.in/page/core_research_grant",
                    "snippet": "Funding for science. This snippet has no closing date.",
                }
            ]
        },
        "grant",
    )
    report = heuristic_venues("idea", store)
    assert report.rows
    assert report.rows[0].deadline == "not found"
    assert report.rows[0].india_relevant is True
