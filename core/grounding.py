"""Drop or flag citations that are not in the evidence store."""

from __future__ import annotations

from typing import Any, Iterable

from pydantic import BaseModel

from core.store import EvidenceStore


def collect_source_ids(obj: Any) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, BaseModel):
            walk(node.model_dump())
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k in {"source_id", "source_ids", "cited_ids"}:
                    if isinstance(v, str):
                        found.append(v)
                    elif isinstance(v, list):
                        found.extend(str(x) for x in v)
                else:
                    walk(v)
            return
        if isinstance(node, list):
            for x in node:
                walk(x)

    walk(obj)
    return found


def ground_model(model: BaseModel, store: EvidenceStore) -> tuple[BaseModel, list[str]]:
    """Replace unknown source IDs with empty / drop list entries. Returns (model, dropped)."""
    known = store.ids()
    dropped: list[str] = []

    def clean(node: Any) -> Any:
        if isinstance(node, list):
            out = []
            for item in node:
                if isinstance(item, str) and item.startswith("SRC-") and item not in known:
                    dropped.append(item)
                    continue
                out.append(clean(item))
            return out
        if isinstance(node, dict):
            data = {k: clean(v) for k, v in node.items()}
            sid = data.get("source_id")
            if isinstance(sid, str) and sid.startswith("SRC-") and sid not in known:
                dropped.append(sid)
                data["source_id"] = ""
                data["ungrounded"] = True
            ids = data.get("source_ids")
            if isinstance(ids, list):
                keep = []
                for x in ids:
                    if isinstance(x, str) and x.startswith("SRC-") and x not in known:
                        dropped.append(x)
                    else:
                        keep.append(x)
                data["source_ids"] = keep
            return data
        return node

    cleaned = clean(model.model_dump())
    return model.__class__.model_validate(cleaned), dropped


def flag_thin_evidence(store: EvidenceStore, min_items: int = 8) -> bool:
    return len(store.all()) < min_items
