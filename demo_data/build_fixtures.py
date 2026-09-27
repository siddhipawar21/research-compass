"""Generate saved SerpApi-shaped fixtures for Demo Mode."""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def scholar_paper(title, link, snippet, authors, year, cited, summary=None):
    """Illustrative hits must not carry URLs that were not returned for that exact record."""
    link = ""
    pubs = [{"name": a} for a in authors]
    return {
        "title": title,
        "link": link,
        "snippet": snippet,
        "publication_info": {
            "summary": summary or f"{authors[0]} et al. - {year}",
            "authors": pubs,
        },
        "inline_links": {"cited_by": {"total": cited, "cites_id": "1"}},
        "year": str(year),
    }


def organic(title, link, snippet, source=None):
    del link  # fixture builders must not attach unverified URLs
    row = {"title": title, "link": "", "snippet": snippet}
    if source:
        row["source"] = source
    return row


def news(title, link, snippet, source, extra_stories=None):
    del link
    row = {
        "title": title,
        "link": "",
        "snippet": snippet,
        "source": {"name": source},
    }
    if extra_stories:
        row["stories"] = extra_stories
    return row


def trends(query, values):
    timeline = []
    for i, v in enumerate(values):
        year = 2021 + i // 12
        month = (i % 12) + 1
        timeline.append(
            {
                "date": f"{year}-{month:02d}",
                "timestamp": str(1609459200 + i * 2500000),
                "values": [{"query": query, "value": str(v), "extracted_value": v}],
            }
        )
    return {"interest_over_time": {"timeline_data": timeline, "averages": [{"query": query, "value": int(sum(values) / len(values))}]}}


def profile(name, author_id, aff, cited, interests):
    # Do not synthesize a Scholar URL. A profile link is stored only if search returned one.
    return {
        "name": name,
        "title": name,
        "link": "",
        "author_id": "",
        "affiliations": aff,
        "snippet": aff,
        "cited_by": cited,
        "interests": [{"title": t} for t in interests],
    }


GNN_SCHOLAR = [
    scholar_paper(
        "Graph neural networks for statistical downscaling of climate data",
        "",
        "A GNN maps coarse GCM fields to station rainfall and outperforms a CNN baseline on extremes.",
        ["L. Chen", "R. Mehta"],
        2022,
        86,
        "L. Chen, R. Mehta - Environmental Data Science 2022",
    ),
    scholar_paper(
        "River-network GNNs for flood forecasting in India",
        "",
        "Graph message passing along river connectivity improves nowcasts in the Krishna basin but fails on ungauged catchments.",
        ["S. Iyer", "P. Nair"],
        2023,
        41,
        "S. Iyer, P. Nair - Hydrology and Earth System Sciences 2023",
    ),
    scholar_paper(
        "Convolutional downscaling of Indian monsoon rainfall",
        "",
        "CNN statistical downscaling is effective for mean monsoon but underperforms on extreme rainfall days.",
        ["A. Sharma", "K. Rao"],
        2021,
        120,
        "A. Sharma, K. Rao - Earth's Future 2021",
    ),
    scholar_paper(
        "Limitations of deep learning weather downscaling: a replication study",
        "",
        "A replication finds that several advertised GNN gains are not significant after leakage-controlled splits.",
        ["M. Vogel", "J. Park"],
        2024,
        18,
        "M. Vogel, J. Park - arXiv 2024",
    ),
    scholar_paper(
        "Graph-based orographic rainfall modelling for the Western Ghats",
        "",
        "Orography-aware graphs improve calibrated rainfall over Kerala; dataset and code promised but incomplete.",
        ["R. Menon", "N. Joshi"],
        2023,
        27,
        "R. Menon, N. Joshi - Climate Dynamics 2023",
    ),
    scholar_paper(
        "Survey of machine learning for climate downscaling",
        "",
        "Review of linear, CNN, GAN, and emerging GNN methods; notes hype around extremes.",
        ["T. Nguyen", "H. Patel"],
        2020,
        310,
        "T. Nguyen, H. Patel - WIREs Climate Change 2020",
    ),
    scholar_paper(
        "District-level monsoon prediction using transformers",
        "",
        "Transformer downscaling on IMD grids demonstrates skill but cannot encode river topology.",
        ["V. Banerjee"],
        2023,
        22,
        "V. Banerjee - arXiv 2023",
    ),
    scholar_paper(
        "Calibration of probabilistic flood early warning in Maharashtra",
        "",
        "Operational warning skill depends more on calibration than on architecture; GNN not used.",
        ["D. Kulkarni", "S. Patil"],
        2022,
        55,
        "D. Kulkarni, S. Patil - Journal of Hydrology 2022",
    ),
]

GNN_RECENT = [
    scholar_paper(
        "Physics-informed graph networks for monsoon extremes over the Western Ghats",
        "",
        "PINN-style message passing reduces bias on orographic extremes versus a pure CNN, with mixed skill on dry-day counts.",
        ["H. Kulkarni", "F. Dias"],
        2024,
        9,
        "H. Kulkarni, F. Dias - Geoscientific Model Development 2024",
    ),
    scholar_paper(
        "Multi-scale catchment graphs for IMD 0.25° rainfall",
        "",
        "Hierarchical graphs over IMD grids improve district MAE but do not beat linear regression on hold-out years.",
        ["Q. Li", "S. Bhat"],
        2025,
        4,
        "Q. Li, S. Bhat - arXiv 2025",
    ),
    scholar_paper(
        "Attention over river graphs for Kerala flood 2018 reanalysis",
        "",
        "Graph attention reconstructs 2018 peaks; authors note the method cannot generalize to ungauged basins in Maharashtra.",
        ["P. Nambiar", "A. George"],
        2024,
        11,
        "P. Nambiar, A. George - Journal of Hydrology 2024",
    ),
    scholar_paper(
        "Satellite-gauge fusion with directed graphs for Indian catchments",
        "",
        "Directed edges following flow accumulation outperform undirected graphs on RMSE; no operational warning evaluation.",
        ["Y. Okada", "R. Pillai"],
        2023,
        16,
        "Y. Okada, R. Pillai - Remote Sensing of Environment 2023",
    ),
    scholar_paper(
        "Temporal graph networks for 6-hour rainfall nowcasts",
        "",
        "TGN nowcasts beat persistence; extreme-day CSI remains below a calibrated analog method.",
        ["E. Rossi", "M. Khan"],
        2022,
        33,
        "E. Rossi, M. Khan - Weather and Forecasting 2022",
    ),
]

GNN_SURVEYS = [
    scholar_paper(
        "A 2024 review of graph learning for hydrometeorology",
        "",
        "Survey of GNNs for floods and rainfall. Flags leakage in spatial cross-validation and limited India-specific datasets.",
        ["C. Alvarez", "B. Sen"],
        2024,
        37,
        "C. Alvarez, B. Sen - WIREs Water 2024",
    ),
    scholar_paper(
        "Benchmarking statistical downscaling: linear, CNN, GAN, GNN",
        "",
        "Head-to-head on CORDEX-SA. GNN wins two of six metrics; linear remains competitive on extremes.",
        ["I. Fernandes", "L. Cho"],
        2023,
        21,
        "I. Fernandes, L. Cho - Climate Dynamics 2023",
    ),
]

GNN_CLAIM = [
    scholar_paper(
        "District watershed graphs for Maharashtra flood early warning",
        "",
        "Prototype maps catchments to nodes for two Maharashtra districts; calibration for Kerala not attempted.",
        ["W. Joshi", "T. Kale"],
        2025,
        2,
        "W. Joshi, T. Kale - arXiv 2025",
    ),
    scholar_paper(
        "Does topology beat pixels for Indian monsoon downscaling?",
        "",
        "Ablation finds river edges help mean rainfall but fail to improve extreme-day CSI versus a CNN.",
        ["G. Raman", "N. Shah"],
        2024,
        7,
        "G. Raman, N. Shah - arXiv 2024",
    ),
    scholar_paper(
        "Calibrated probabilistic GNNs for catchment-scale rainfall",
        "",
        "Reliability diagrams improve after temperature scaling; authors do not claim operational readiness.",
        ["S. Iqbal", "K. Roy"],
        2023,
        14,
        "S. Iqbal, K. Roy - Journal of Hydrometeorology 2023",
    ),
]


def gnn_fixture():
    q_main = "graph neural monsoon rainfall downscaling"
    return [
        {
            "engine": "google_scholar",
            "purpose": "closest papers",
            "params": {"q": q_main, "num": "10", "hl": "en"},
            "response": {"organic_results": GNN_SCHOLAR},
        },
        {
            "engine": "google_scholar",
            "purpose": "recent papers",
            "params": {"q": q_main, "num": "10", "hl": "en", "as_ylo": "2022"},
            "response": {"organic_results": GNN_RECENT},
        },
        {
            "engine": "google_scholar",
            "purpose": "surveys",
            "params": {"q": f"{q_main} review OR survey", "num": "8", "hl": "en"},
            "response": {"organic_results": GNN_SURVEYS},
        },
        {
            "engine": "google",
            "purpose": "code",
            "params": {"q": f"{q_main} site:github.com"},
            "response": {
                "organic_results": [
                    organic(
                        "iyer-lab/river-gnn",
                        "",
                        "PyTorch Geometric flood GNN. README lacks tests and Maharashtra district graphs.",
                    ),
                    organic(
                        "climate-ml/downscale-cnn",
                        "",
                        "CNN downscaling baseline used in several papers. Apache-2 license.",
                    ),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "datasets",
            "params": {
                "q": f"{q_main} dataset OR benchmark site:huggingface.co OR site:paperswithcode.com OR site:kaggle.com"
            },
            "response": {
                "organic_results": [
                    organic(
                        "IMD gridded rainfall on Kaggle",
                        "",
                        "0.25 degree IMD rainfall grids. Not district-level watersheds.",
                    ),
                    organic(
                        "Papers with Code: climate downscaling",
                        "",
                        "Benchmarks list CNN and GAN methods; few GNN entries.",
                    ),
                ]
            },
        },
        {
            "engine": "google_news",
            "purpose": "news",
            "params": {"q": q_main, "hl": "en", "gl": "in"},
            "response": {
                "news_results": [
                    news(
                        "IITs tout AI for monsoon flood warnings",
                        "",
                        "Labs say graph models enable earlier warnings. Independent verification limited.",
                        "The Hindu",
                        extra_stories=[
                            {
                                "title": "Scientists warn of hype in AI weather products",
                                "link": "",
                                "source": {"name": "The Indian Express"},
                                "snippet": "Several downscaling claims fail outside the training basin.",
                            }
                        ],
                    ),
                    news(
                        "Maharashtra tests district flood dashboards",
                        "",
                        "Pilot uses statistical downscaling, not a GNN.",
                        "Hindustan Times",
                    ),
                ]
            },
        },
        {
            "engine": "google_trends",
            "purpose": "interest over time",
            "params": {"q": "climate downscaling", "data_type": "TIMESERIES", "date": "today 5-y"},
            "response": trends("climate downscaling", [18, 20, 19, 22, 21, 25, 24, 28, 30, 29, 33, 31, 34, 36, 35, 40, 42, 39, 44, 47, 45, 48, 52, 50]),
        },
        {
            "engine": "google_scholar_profiles",
            "purpose": "authors",
            "params": {"mauthors": "graph neural monsoon rainfall", "hl": "en"},
            "response": {
                "profiles": [
                    profile("S. Iyer", "", "IIT Bombay, Civil Engineering", 2100, ["hydrology", "graphs"]),
                    profile("R. Menon", "", "IISc Bangalore, Divecha Centre", 980, ["monsoon", "orography"]),
                    profile("A. Sharma", "", "IIT Delhi, Atmospheric Science", 3400, ["monsoon", "downscaling"]),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "venues",
            "params": {"q": f"{q_main} conference OR workshop CFP 2026 OR 2027"},
            "response": {
                "organic_results": [
                    organic(
                        "NeurIPS 2026 Call for Papers",
                        "",
                        "Machine learning conference. Abstract deadline May 15 2026. Climate workshop TBD.",
                    ),
                    organic(
                        "Climate Change AI workshop at ICLR",
                        "",
                        "Workshop on ML for climate. Submission deadline not listed on this result.",
                    ),
                    organic(
                        "COMSNETS 2027 (Bengaluru)",
                        "",
                        "India-based systems conference; hydrology papers out of scope. Deadline not found here.",
                    ),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "india grants",
            "params": {"q": f"{q_main} india grant OR fellowship OR SERB OR DST OR ANRF"},
            "response": {
                "organic_results": [
                    organic(
                        "ANRF / SERB Core Research Grant",
                        "",
                        "India grant for science and engineering. This snippet does not include a deadline.",
                    ),
                    organic(
                        "DST National Mission on Strategic Knowledge for Climate Change",
                        "",
                        "Climate programme in India. Call dates not present in the snippet.",
                    ),
                    organic(
                        "India AI Fellowship 2026",
                        "",
                        "Fellowship for AI researchers in India. Application due 30 Sep 2026.",
                    ),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "contradictions",
            "params": {"q": f"{q_main} limitation OR fails OR contradictory OR replication"},
            "response": {
                "organic_results": [
                    organic(
                        "Why GNN downscaling results fail to beat linear baselines",
                        "",
                        "Negative result: after leakage control, GNN does not beat linear statistical downscaling on extremes.",
                    ),
                    organic(
                        "Blog: the overfit monsoon model",
                        "",
                        "Blog post argues operational agencies cannot deploy unpublished GNN checkpoints.",
                    ),
                ]
            },
        },
        {
            "engine": "google_scholar",
            "purpose": "claim-like titles",
            "params": {"q": "graph neural network that downscales Indian monsoon rainfall", "num": "8", "hl": "en"},
            "response": {"organic_results": GNN_CLAIM},
        },
    ]


ASR_SCHOLAR = [
    scholar_paper(
        "wav2vec 2.0: A framework for self-supervised learning of speech representations",
        "",
        "Self-supervised speech pretraining outperforms supervised baselines with limited labeled data.",
        ["A. Baevski", "H. Zhou"],
        2020,
        8900,
        "A. Baevski et al. - NeurIPS 2020",
    ),
    scholar_paper(
        "IndicWav2Vec: multilingual speech representations for Indian languages",
        "",
        "Multilingual SSL for Indic languages demonstrates strong transfer; Kannada and Marathi included. Noisy telephone speech remains hard.",
        ["T. Javed", "K. Bhogale"],
        2022,
        210,
        "T. Javed, K. Bhogale - Interspeech 2022",
    ),
    scholar_paper(
        "MUCS 2021: multilingual and code-switching ASR challenges for low resource Indian languages",
        "",
        "Challenge data and baselines for Indian ASR. Supervised Conformers still strong when 300 hours exist.",
        ["A. Diwan", "R. Vaideeswaran"],
        2021,
        180,
        "A. Diwan et al. - Interspeech 2021",
    ),
    scholar_paper(
        "Limitations of self-supervised speech models on noisy conversational telephony",
        "",
        "SSL encoders fail to match supervised models on highly noisy conversational test sets without domain-matched unlabeled data.",
        ["P. Gupta", "L. Wong"],
        2023,
        44,
        "P. Gupta, L. Wong - ASRU 2023",
    ),
    scholar_paper(
        "Bhojpuri speech resources and ASR baselines",
        "",
        "Low-resource Bhojpuri ASR; 20 hours labeled is typical. Community-radio audio not covered.",
        ["S. Singh", "M. Rai"],
        2022,
        19,
        "S. Singh, M. Rai - LREC 2022",
    ),
    scholar_paper(
        "A survey of speech recognition for Indian languages",
        "",
        "Survey of ASR for Indic languages including tokenizers and multilingual encoders.",
        ["B. Deka", "C. Nath"],
        2021,
        95,
        "B. Deka, C. Nath - Language Resources and Evaluation 2021",
    ),
    scholar_paper(
        "Fine-tuning wav2vec 2.0 for Kannada with 20 hours of data",
        "",
        "20-hour fine-tune achieves competitive WER on read speech but underperforms on conversations.",
        ["N. Hegde"],
        2023,
        12,
        "N. Hegde - arXiv 2023",
    ),
]


ASR_RECENT = [
    scholar_paper(
        "Telephone-domain continued pretraining for Marathi ASR",
        "",
        "Continued SSL on call-center audio lowers Marathi WER; Bhojpuri transfer is weak without in-domain unlabeled data.",
        ["R. Kulkarni", "D. Bose"],
        2024,
        8,
        "R. Kulkarni, D. Bose - Interspeech 2024",
    ),
    scholar_paper(
        "Community-radio unlabeled speech for Kannada wav2vec",
        "",
        "Radio crawl helps read-speech WER but fails on noisy conversational telephony without augmentation.",
        ["M. Rao", "L. Fernandes"],
        2025,
        3,
        "M. Rao, L. Fernandes - arXiv 2025",
    ),
    scholar_paper(
        "Shared subword tokenizers across Indic SSL encoders",
        "",
        "A single tokenizer transfers to unseen Indic languages on read speech; conversational sets still need language-specific vocab.",
        ["A. Iyer", "P. Das"],
        2023,
        17,
        "A. Iyer, P. Das - ACL Findings 2023",
    ),
    scholar_paper(
        "20-hour fine-tunes versus 300-hour Conformers on MUCS conversational splits",
        "",
        "SSL with 20 hours does not beat a 300-hour supervised Conformer on the conversational test sets.",
        ["J. Thomas", "S. Nair"],
        2022,
        29,
        "J. Thomas, S. Nair - SLT 2022",
    ),
]

ASR_SURVEYS = [
    scholar_paper(
        "Self-supervised speech for South Asian languages: a 2024 survey",
        "",
        "Reviews wav2vec, HuBERT, and w2v-BERT for Indic ASR. Highlights telephone-domain mismatch and missing Bhojpuri unlabeled corpora.",
        ["K. Malik", "E. Chen"],
        2024,
        15,
        "K. Malik, E. Chen - APSIPA 2024",
    ),
    scholar_paper(
        "Code-switching evaluation pitfalls in Indian ASR challenges",
        "",
        "Survey of MUCS and related tasks; notes that WER on mixed speech is not comparable across tokenizers.",
        ["H. Banerjee", "V. Shah"],
        2023,
        22,
        "H. Banerjee, V. Shah - Computer Speech & Language 2023",
    ),
]

ASR_CLAIM = [
    scholar_paper(
        "A multilingual encoder for Marathi, Bhojpuri, and Kannada without a new tokenizer",
        "",
        "Shared encoder claim tested on read speech only; authors do not evaluate noisy conversational telephone sets.",
        ["F. Rahman", "N. Patil"],
        2025,
        1,
        "F. Rahman, N. Patil - arXiv 2025",
    ),
    scholar_paper(
        "Low-resource telephony ASR with 20 hours of labeled Bhojpuri",
        "",
        "20-hour fine-tune matches a larger supervised model on broadcast news and underperforms on calls.",
        ["S. Yadav", "C. Moore"],
        2024,
        6,
        "S. Yadav, C. Moore - arXiv 2024",
    ),
    scholar_paper(
        "Does unlabeled radio speech close the Indic telephony gap?",
        "",
        "Radio pretraining helps Kannada read WER; conversational telephone WER does not match a 300-hour Conformer.",
        ["L. Gomez", "A. Krishnan"],
        2023,
        10,
        "L. Gomez, A. Krishnan - Interspeech 2023",
    ),
]


def asr_fixture():
    q = "self-supervised ASR Marathi Bhojpuri Kannada"
    return [
        {"engine": "google_scholar", "purpose": "closest papers", "params": {"q": q, "num": "10", "hl": "en"}, "response": {"organic_results": ASR_SCHOLAR}},
        {"engine": "google_scholar", "purpose": "recent", "params": {"q": q, "num": "10", "hl": "en", "as_ylo": "2022"}, "response": {"organic_results": ASR_RECENT}},
        {"engine": "google_scholar", "purpose": "surveys", "params": {"q": f"{q} review OR survey", "num": "8", "hl": "en"}, "response": {"organic_results": ASR_SURVEYS}},
        {
            "engine": "google",
            "purpose": "code",
            "params": {"q": f"{q} site:github.com"},
            "response": {
                "organic_results": [
                    organic("AI4Bharat/IndicWav2Vec", "", "Official IndicWav2Vec code and models. Strong starting point."),
                    organic("facebookresearch/fairseq", "", "wav2vec 2.0 reference implementation."),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "datasets",
            "params": {"q": f"{q} dataset site:huggingface.co OR site:paperswithcode.com OR site:kaggle.com"},
            "response": {
                "organic_results": [
                    organic("ai4bharat/indicwav2vec models", "", "Hugging Face checkpoints for Indic SSL speech."),
                    organic("MUCS 2021 datasets", "", "Multilingual Indian ASR challenge data."),
                ]
            },
        },
        {
            "engine": "google_news",
            "purpose": "news",
            "params": {"q": q, "hl": "en", "gl": "in"},
            "response": {
                "news_results": [
                    news("Bhashini and AI4Bharat expand Indian language speech models", "", "Public-sector push for Indic ASR. Independent WER on telephone speech not reported.", "Economic Times"),
                    news("Startups claim near-human ASR in regional languages", "", "Marketing claims often fail on noisy conversational audio.", "Mint"),
                ]
            },
        },
        {
            "engine": "google_trends",
            "purpose": "trends",
            "params": {"q": "indic asr", "data_type": "TIMESERIES", "date": "today 5-y"},
            "response": trends("indic asr", [8, 9, 9, 12, 11, 14, 18, 17, 22, 24, 28, 27, 30, 33, 31, 36, 38, 40, 41, 39, 42, 44, 43, 46]),
        },
        {
            "engine": "google_scholar_profiles",
            "purpose": "authors",
            "params": {"mauthors": "IndicWav2Vec ASR", "hl": "en"},
            "response": {
                "profiles": [
                    profile("T. Javed", "", "AI4Bharat / IIT Madras", 1500, ["speech", "Indic NLP"]),
                    profile("A. Diwan", "", "IIT Bombay", 800, ["ASR", "code-switching"]),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "venues",
            "params": {"q": f"{q} conference OR workshop CFP 2026"},
            "response": {
                "organic_results": [
                    organic("Interspeech 2026 Call for Papers", "", "Speech conference. Paper deadline 12 Feb 2026."),
                    organic("ICON 2026 NLP conference India", "", "India NLP conference. Deadline not listed in this snippet."),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "grants",
            "params": {"q": f"{q} Bhashini grant OR MeitY OR SERB"},
            "response": {
                "organic_results": [
                    organic("Bhashini Challenge grants", "", "MeitY Bhashini programme. Deadline not found in snippet."),
                    organic("SERB SIRE fellowship", "", "India fellowship. This result does not include a deadline."),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "contradictions",
            "params": {"q": f"{q} limitation OR fails OR noisy telephone"},
            "response": {
                "organic_results": [
                    organic(
                        "SSL speech models underperform on telephony",
                        "",
                        "Does not beat a 300-hour supervised Conformer on noisy conversational tests.",
                    )
                ]
            },
        },
        {
            "engine": "google_scholar",
            "purpose": "claim-like",
            "params": {"q": "pretrain wav2vec Marathi Bhojpuri Kannada 20 hours", "num": "8", "hl": "en"},
            "response": {"organic_results": ASR_CLAIM},
        },
    ]


FED_SCHOLAR = [
    scholar_paper(
        "Communication-efficient learning of deep networks from decentralized data",
        "",
        "FedAvg demonstrates that averaging locally trained models can approach centralized accuracy.",
        ["H. B. McMahan"],
        2017,
        25000,
        "H. B. McMahan et al. - AISTATS 2017",
    ),
    scholar_paper(
        "Federated learning for healthcare: a tutorial and survey",
        "",
        "Survey of FL in health. Notes non-IID clinics and intermittent connectivity as open problems.",
        ["J. Xu", "B. Glicksberg"],
        2021,
        640,
        "J. Xu et al. - ACM Computing Surveys 2021",
    ),
    scholar_paper(
        "Privacy accounting for federated medical triage models",
        "",
        "Simple DP-FedAvg often cannot match a centralized baseline at epsilon values hospitals accept.",
        ["A. Narayan", "L. Chen"],
        2022,
        73,
        "A. Narayan, L. Chen - CHIL 2022",
    ),
    scholar_paper(
        "Learning from rural primary care data in India: a centralized EHR study",
        "",
        "Centralized models for referral triage in Indian PHCs. No federated training.",
        ["R. Deshmukh", "P. Iyer"],
        2020,
        48,
        "R. Deshmukh, P. Iyer - Journal of Biomedical Informatics 2020",
    ),
    scholar_paper(
        "Non-IID federated optimization fails under clinic shift",
        "",
        "FedAvg underperforms when client distributions differ strongly; personalization required.",
        ["Y. Zhao"],
        2018,
        2100,
        "Y. Zhao et al. - arXiv 2018",
    ),
    scholar_paper(
        "On-device inference for community health workers",
        "",
        "Connectivity-aware deployment in rural India; training still centralized.",
        ["K. Bose", "S. Reddy"],
        2023,
        15,
        "K. Bose, S. Reddy - COMPASS 2023",
    ),
]


FED_RECENT = [
    scholar_paper(
        "Intermittent connectivity in federated PHC training",
        "",
        "Drop-and-resume FedAvg over simulated rural links loses 4–7 points versus always-on clients; no differential privacy.",
        ["M. Rao", "T. Singh"],
        2024,
        6,
        "M. Rao, T. Singh - COMPASS 2024",
    ),
    scholar_paper(
        "Personalization layers for non-IID clinic triage",
        "",
        "Local heads recover accuracy under clinic shift; global FedAvg still underperforms a centralized baseline.",
        ["H. Park", "R. Mehta"],
        2025,
        3,
        "H. Park, R. Mehta - CHIL 2025",
    ),
    scholar_paper(
        "On-device vitals models for ASHA workers in Bihar",
        "",
        "Inference on-device with centralized training. Federated updates were out of scope.",
        ["A. Kumari", "S. Joseph"],
        2023,
        12,
        "A. Kumari, S. Joseph - ICTD 2023",
    ),
]

FED_SURVEYS = [
    scholar_paper(
        "Federated learning in low-resource health systems: a review",
        "",
        "Review covering connectivity, DP, and non-IID clinics. India PHC deployments remain scarce in the literature.",
        ["D. Okonkwo", "L. Berg"],
        2024,
        19,
        "D. Okonkwo, L. Berg - npj Digital Medicine 2024",
    ),
    scholar_paper(
        "Differential privacy versus utility in medical federated averaging",
        "",
        "Survey of DP-FedAvg. Simple noise schedules cannot match centralized referral accuracy at hospital-accepted epsilon.",
        ["C. Walsh", "P. Gupta"],
        2023,
        28,
        "C. Walsh, P. Gupta - JAMIA 2023",
    ),
]

FED_CLAIM = [
    scholar_paper(
        "Federated averaging across primary health centres without sharing records",
        "",
        "Simulated PHCs show FedAvg close to centralized accuracy only without DP; with DP the gap reopens.",
        ["N. Verma", "J. Cole"],
        2025,
        2,
        "N. Verma, J. Cole - arXiv 2025",
    ),
    scholar_paper(
        "Non-IID rural clinic populations break vanilla FedAvg",
        "",
        "Synthetic non-IID splits of Indian PHC-like features; vanilla averaging underperforms local models.",
        ["E. D'Souza", "K. Amin"],
        2024,
        5,
        "E. D'Souza, K. Amin - arXiv 2024",
    ),
    scholar_paper(
        "Simple DP noise on symptom-and-vitals triage",
        "",
        "Epsilon budgets used in hospitals cause the federated model not to match a centralized baseline.",
        ["B. Liu", "A. Raman"],
        2023,
        9,
        "B. Liu, A. Raman - PMLR 2023",
    ),
]


def fed_fixture():
    q = "federated learning rural telemedicine India"
    return [
        {"engine": "google_scholar", "purpose": "closest papers", "params": {"q": q, "num": "10", "hl": "en"}, "response": {"organic_results": FED_SCHOLAR}},
        {"engine": "google_scholar", "purpose": "recent", "params": {"q": q, "num": "10", "hl": "en", "as_ylo": "2022"}, "response": {"organic_results": FED_RECENT}},
        {"engine": "google_scholar", "purpose": "surveys", "params": {"q": f"{q} review OR survey", "num": "8", "hl": "en"}, "response": {"organic_results": FED_SURVEYS}},
        {
            "engine": "google",
            "purpose": "code",
            "params": {"q": f"{q} site:github.com"},
            "response": {
                "organic_results": [
                    organic("adap/flower", "", "Federated learning framework. No PHC triage case in this snippet."),
                    organic("OpenMined/PySyft", "", "Privacy-preserving ML toolkit."),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "datasets",
            "params": {"q": f"{q} dataset site:huggingface.co OR site:kaggle.com"},
            "response": {
                "organic_results": [
                    organic("Synthetic symptom datasets on Kaggle", "", "Not rural Indian PHC records. Real EHR sharing restricted."),
                ]
            },
        },
        {
            "engine": "google_news",
            "purpose": "news",
            "params": {"q": q, "hl": "en", "gl": "in"},
            "response": {
                "news_results": [
                    news("NHA discusses federated architecture for ABDM", "", "Policy interest in not pooling raw records. No published triage accuracy.", "Business Standard"),
                    news("Telemedicine startups pitch on-device AI", "", "Hype around privacy-preserving triage; independent trials thin.", "Moneycontrol"),
                ]
            },
        },
        {
            "engine": "google_trends",
            "purpose": "trends",
            "params": {"q": "federated learning", "data_type": "TIMESERIES", "date": "today 5-y"},
            "response": trends("federated learning", [30, 32, 31, 35, 40, 38, 42, 48, 47, 45, 44, 43, 41, 40, 42, 39, 38, 37, 36, 35, 34, 36, 35, 33]),
        },
        {
            "engine": "google_scholar_profiles",
            "purpose": "authors",
            "params": {"mauthors": "federated learning healthcare India", "hl": "en"},
            "response": {
                "profiles": [
                    profile("R. Deshmukh", "", "AIIMS / public health informatics", 900, ["EHR", "PHC"]),
                    profile("K. Bose", "", "IIIT Hyderabad, social computing", 400, ["HCI", "health"]),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "venues",
            "params": {"q": f"{q} conference COMPASS CHIL CFP 2026"},
            "response": {
                "organic_results": [
                    organic("ACM COMPASS 2026", "", "Computing and sustainable societies. Deadline 3 Mar 2026."),
                    organic("CHIL 2026 Call", "", "Conference on health, inference, and learning. Deadline not found."),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "grants",
            "params": {"q": f"{q} ICMR DBT grant fellowship India"},
            "response": {
                "organic_results": [
                    organic("ICMR extra-mural grants", "", "Health research grants in India. Deadline not found in this snippet."),
                    organic("DBT BIRAC biotechnology grants", "", "India biotech funding. Dates not listed here."),
                ]
            },
        },
        {
            "engine": "google",
            "purpose": "contradictions",
            "params": {"q": f"{q} does not match centralized OR non-IID fails"},
            "response": {
                "organic_results": [
                    organic(
                        "DP-FedAvg cannot match centralized referral accuracy",
                        "",
                        "Simple differential privacy does not match a centralized baseline at practical epsilon.",
                    )
                ]
            },
        },
        {
            "engine": "google_scholar",
            "purpose": "claim-like",
            "params": {"q": "federated averaging differential privacy primary health centres India", "num": "8", "hl": "en"},
            "response": {"organic_results": FED_CLAIM},
        },
    ]


def main():
    mapping = {
        "gnn_climate.json": gnn_fixture(),
        "indic_asr.json": asr_fixture(),
        "fed_telemed.json": fed_fixture(),
    }
    for name, data in mapping.items():
        path = OUT / name
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"wrote {path} ({len(data)} searches)")


if __name__ == "__main__":
    main()
