"""Persist Analyze runs in the same SQLite file as the SerpApi cache."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from core.pipeline import CompassReport
from core.planner import QueryPlan
from core.store import EvidenceItem, EvidenceStore
from modules.contradictions import ContradictionsReport
from modules.debate import DebateReport
from modules.experts import ExpertsReport
from modules.novelty import NoveltyReport
from modules.radar import RadarReport
from modules.reproducibility import ReproducibilityReport
from modules.venues import VenuesReport


class SavedReport(BaseModel):
    abstract: str
    mode: str
    sample_id: str | None = None
    plan: QueryPlan
    novelty: NoveltyReport
    contradictions: ContradictionsReport
    debate: DebateReport
    reproducibility: ReproducibilityReport
    radar: RadarReport
    experts: ExpertsReport
    venues: VenuesReport
    evidence: list[EvidenceItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @classmethod
    def from_compass(cls, report: CompassReport) -> "SavedReport":
        return cls(
            abstract=report.abstract,
            mode=report.mode,
            sample_id=report.sample_id,
            plan=report.plan,
            novelty=report.novelty,
            contradictions=report.contradictions,
            debate=report.debate,
            reproducibility=report.reproducibility,
            radar=report.radar,
            experts=report.experts,
            venues=report.venues,
            evidence=list(report.store.all()),
            notes=list(report.notes),
        )

    def to_compass(self) -> CompassReport:
        store = EvidenceStore()
        for item in self.evidence:
            store.add(item)
        return CompassReport(
            abstract=self.abstract,
            mode=self.mode,
            sample_id=self.sample_id,
            plan=self.plan,
            novelty=self.novelty,
            contradictions=self.contradictions,
            debate=self.debate,
            reproducibility=self.reproducibility,
            radar=self.radar,
            experts=self.experts,
            venues=self.venues,
            store=store,
            searches=[],
            notes=list(self.notes),
        )


def verdict_label(report: CompassReport | SavedReport) -> str:
    debate = report.debate
    text = (debate.verdict or "").lower()
    if debate.advocate_score > debate.skeptic_score or (
        "pursue" in text and "do not" not in text and "don't" not in text
    ):
        return "Pursue"
    if debate.skeptic_score > debate.advocate_score or "do not" in text or "don't" in text:
        return "Hold"
    return "Split"


def relative_time(created_at: float, now: float | None = None) -> str:
    now = time.time() if now is None else now
    delta = max(0, now - created_at)
    if delta < 45:
        return "just now"
    if delta < 3600:
        n = max(1, int(delta // 60))
        return f"{n} minute{'s' if n != 1 else ''} ago"
    if delta < 86400:
        n = max(1, int(delta // 3600))
        return f"{n} hour{'s' if n != 1 else ''} ago"
    n = max(1, int(delta // 86400))
    return f"{n} day{'s' if n != 1 else ''} ago"


@dataclass
class HistoryRow:
    id: int
    created_at: float
    mode: str
    abstract_text: str
    novelty_score: int
    verdict_label: str
    radar_label: str


class RunHistory:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    mode TEXT NOT NULL,
                    abstract_text TEXT NOT NULL,
                    novelty_score INTEGER,
                    verdict_label TEXT,
                    radar_label TEXT,
                    report_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, report: CompassReport) -> int:
        saved = SavedReport.from_compass(report)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO runs
                (created_at, mode, abstract_text, novelty_score, verdict_label, radar_label, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    report.mode,
                    report.abstract,
                    int(report.novelty.score),
                    verdict_label(report),
                    report.radar.label,
                    saved.model_dump_json(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_recent(self, limit: int = 15) -> list[HistoryRow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, mode, abstract_text, novelty_score, verdict_label, radar_label
                FROM runs ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            HistoryRow(
                id=int(r["id"]),
                created_at=float(r["created_at"]),
                mode=r["mode"],
                abstract_text=r["abstract_text"] or "",
                novelty_score=int(r["novelty_score"] or 0),
                verdict_label=r["verdict_label"] or "",
                radar_label=r["radar_label"] or "",
            )
            for r in rows
        ]

    def load(self, run_id: int) -> CompassReport:
        with self._connect() as conn:
            row = conn.execute("SELECT report_json FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise KeyError(f"No saved run {run_id}")
        saved = SavedReport.model_validate_json(row["report_json"])
        return saved.to_compass()

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM runs")
            conn.commit()

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()
        return int(row["n"] if row else 0)
