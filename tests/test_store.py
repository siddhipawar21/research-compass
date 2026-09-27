from core.store import EvidenceStore, infer_source_type, validate_source_ids


SCHOLAR_PAYLOAD = {
    "organic_results": [
        {
            "title": "Graph neural networks for downscaling climate data",
            "link": "https://arxiv.org/abs/1234",
            "snippet": "We propose a GNN for statistical downscaling.",
            "publication_info": {
                "summary": "A Researcher - Nature Climate 2022",
                "authors": [{"name": "A Researcher"}],
            },
            "inline_links": {"cited_by": {"total": 42}},
            "year": "2022",
        }
    ]
}

NEWS_PAYLOAD = {
    "news_results": [
        {
            "title": "Climate models get a graph upgrade",
            "link": "https://www.thehindu.com/climate-gnn",
            "source": {"name": "The Hindu"},
            "snippet": "Indian labs test GNN downscaling.",
            "date": "2 days ago",
            "stories": [
                {
                    "title": "Skeptical take on hype",
                    "link": "https://news.example.com/skeptic",
                    "source": {"name": "Example News"},
                    "snippet": "Results fail to beat linear baselines.",
                }
            ],
        }
    ]
}


def test_scholar_normalization_extracts_year_and_citations():
    store = EvidenceStore()
    items = store.ingest_search("google_scholar", SCHOLAR_PAYLOAD, "gnn climate")
    assert len(items) == 1
    item = items[0]
    assert item.id == "SRC-001"
    assert item.source_type == "paper"
    assert item.quality == "peer_reviewed"
    assert item.year == 2022
    assert item.cited_by == 42
    assert "A Researcher" in item.authors
    assert item.url.startswith("https://arxiv.org")


def test_news_flattens_nested_stories():
    store = EvidenceStore()
    items = store.ingest_search("google_news", NEWS_PAYLOAD, "climate gnn")
    titles = {i.title for i in items}
    assert "Climate models get a graph upgrade" in titles
    assert "Skeptical take on hype" in titles
    assert all(i.source_type == "news" for i in items)


def test_github_typed_from_google():
    store = EvidenceStore()
    payload = {
        "organic_results": [
            {
                "title": "org/climate-gnn",
                "link": "https://github.com/org/climate-gnn",
                "snippet": "PyTorch implementation",
            }
        ]
    }
    items = store.ingest_search("google", payload, "site:github.com climate gnn")
    assert items[0].source_type == "github"
    assert infer_source_type("google", items[0].url) == "github"


def test_citation_id_validation():
    store = EvidenceStore()
    store.ingest_search("google_scholar", SCHOLAR_PAYLOAD, "q")
    valid, invalid = validate_source_ids(["SRC-001", "SRC-999", ""], store)
    assert valid == ["SRC-001"]
    assert invalid == ["SRC-999"]
