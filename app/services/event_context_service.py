from __future__ import annotations

from typing import Any


def _pick(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def normalize_event_card(item: dict[str, Any]) -> dict[str, Any]:
    region_obj = item.get("region") if isinstance(item, dict) else None
    region_name = ""
    if isinstance(region_obj, dict):
        region_name = _pick(region_obj.get("regionName"), region_obj.get("name"), "") or ""
    region_name = _pick(region_name, item.get("lotNumberAdr"), "") or ""

    event_id = _pick(item.get("eventId"), item.get("id"), item.get("event_id"))
    status = _pick(item.get("eventStatus"), item.get("status"), "") or ""
    return {
        "eventId": int(event_id) if event_id is not None else 0,
        "title": str(_pick(item.get("title"), "추천 행사")),
        "description": str(_pick(item.get("simpleExplain"), item.get("description"), item.get("eventDesc"), "")),
        "thumbnail": str(_pick(item.get("thumbnail"), item.get("thumbUrl"), item.get("imageUrl"), "")),
        "region": str(region_name),
        "startDate": str(_pick(item.get("startDate"), item.get("start_date"), "")),
        "endDate": str(_pick(item.get("endDate"), item.get("end_date"), "")),
        "eventStatus": str(status),
        "applyUrl": f"/events/{int(event_id)}/apply" if event_id is not None and status == "행사참여모집중" else "",
    }
