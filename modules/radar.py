"""Topic radar from Trends, News, and Scholar years already in the store."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from core.grounding import flag_thin_evidence, ground_model
from core.llm import complete_json
from core.store import EvidenceStore

SYSTEM = (
    "Label the topic Rising, Stable, Fading, or Hype using ONLY Google Trends timeline "
    "points, news hits, and Scholar years in the evidence list. Cite source_ids. No invented stats."
)


class YearCount(BaseModel):
    year: int
    papers: int


class TrendPoint(BaseModel):
    date: str
    value: float


class RadarReport(BaseModel):
    label: str  # Rising | Stable | Fading | Hype
    confidence: float = 0.4
    thin_evidence: bool = False
    reasoning: str
    scholar_by_year: list[YearCount] = Field(default_factory=list)
    trend_points: list[TrendPoint] = Field(default_factory=list)
    news_count: int = 0
    source_ids: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


def _trend_series(store: EvidenceStore) -> tuple[list[TrendPoint], list[str]]:
    points: list[TrendPoint] = []
    ids: list[str] = []
    for item in store.filter(engine="google_trends"):
        ids.append(item.id)
        timeline = (item.extra or {}).get("timeline_data") or []
        for row in timeline:
            if not isinstance(row, dict):
                continue
            date = str(row.get("date") or row.get("timestamp") or "")
            values = row.get("values") or []
            val = 0.0
            if isinstance(values, list) and values:
                v0 = values[0] if isinstance(values[0], dict) else {}
                try:
                    val = float(v0.get("extracted_value") if v0.get("extracted_value") is not None else v0.get("value") or 0)
                except (TypeError, ValueError):
                    val = 0.0
            elif isinstance(row.get("value"), (int, float)):
                val = float(row["value"])
            if date:
                points.append(TrendPoint(date=date, value=val))
    return points, ids


def _slope(values: list[float]) -> float:
    if len(values) < 4:
        return 0.0
    mid = len(values) // 2
    a = sum(values[:mid]) / max(1, mid)
    b = sum(values[mid:]) / max(1, len(values) - mid)
    return b - a


def heuristic_radar(abstract: str, store: EvidenceStore) -> RadarReport:
    thin = flag_thin_evidence(store)
    years = store.publication_years()
    scholar_rows = [YearCount(year=y, papers=n) for y, n in years.items()]
    news = store.filter(source_type="news")
    points, trend_ids = _trend_series(store)
    values = [p.value for p in points]
    slope = _slope(values)
    recent = sum(n for y, n in years.items() if y >= 2023)
    older = sum(n for y, n in years.items() if y < 2023)
    news_n = len(news)
    if news_n >= 6 and recent <= 2 and slope > 5:
        label = "Hype"
        why = "News volume is high relative to Scholar papers in the store, with a rising Trends slope."
    elif slope > 8 or (recent > older and recent >= 3):
        label = "Rising"
        why = "Recent Scholar years and/or Google Trends values in the store trend upward."
    elif slope < -8 or (older > recent * 2 and older >= 4):
        label = "Fading"
        why = "Older Scholar hits dominate, or Trends values decline in the stored timeline."
    else:
        label = "Stable"
        why = "Scholar year counts and Trends values in the store do not show a strong directional move."
    ids = trend_ids + [i.id for i in store.filter(source_type="paper")[:8]] + [n.id for n in news[:5]]
    if not points and not years:
        thin = True
        why += " Trends and year histograms are missing, so the label is weakly supported."
    conf = 0.28 if thin else min(0.72, 0.4 + 0.02 * (len(points) // 8 + len(years)))
    return RadarReport(
        label=label,
        confidence=round(conf, 2),
        thin_evidence=thin,
        reasoning=why,
        scholar_by_year=scholar_rows,
        trend_points=points[:80],
        news_count=news_n,
        source_ids=list(dict.fromkeys(ids)),
    )


def analyze_radar(
    abstract: str,
    store: EvidenceStore,
    *,
    use_llm: bool = False,
    llm_kwargs: dict[str, Any] | None = None,
    complete: Callable[..., RadarReport] | None = None,
) -> RadarReport:
    fallback = heuristic_radar(abstract, store)
    if not use_llm:
        return fallback
    fn = complete or complete_json
    try:
        report = fn(
            SYSTEM,
            f"Abstract:\n{abstract}\n\nEvidence:\n{store.to_llm_context()}\n"
            f"Precomputed scholar years: {fallback.scholar_by_year}\n"
            f"News count: {fallback.news_count}\nTrend points (sample): {fallback.trend_points[:12]}",
            RadarReport,
            **(llm_kwargs or {}),
        )
        report, dropped = ground_model(report, store)
        report.dropped_citations = dropped
        report.scholar_by_year = fallback.scholar_by_year
        report.trend_points = fallback.trend_points
        report.news_count = fallback.news_count
        return report
    except Exception:
        return fallback
