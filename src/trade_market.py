"""Source-attributed market sanity checks, separate from category utility."""

import math
from datetime import datetime, timedelta


def _number(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    return value > 0 if positive else value >= 0


def assess_market(context, bundle, proposal):
    """Never sum ordinal ranks or invent market data from our model's rankings."""
    snapshot = bundle.get("market_snapshot")
    policy = bundle.get("market_policy", {})
    max_age = policy.get("max_age_days", 7)
    max_ratio = policy.get("max_value_ratio", 1.75)
    elite = policy.get("elite_rank", 20)
    rank_gap = policy.get("extreme_rank_gap", 50)
    if (
        not _number(max_age, True)
        or not _number(max_ratio, True)
        or max_ratio < 1
        or type(elite) is not int
        or elite < 1
        or type(rank_gap) is not int
        or rank_gap < 1
    ):
        raise ValueError("Invalid market policy: positive age/rank limits and ratio >= 1 required")
    result = {
        "status": "unavailable",
        "blocked": False,
        "requires_review": True,
        "source": None,
        "captured_at": None,
        "reasons": [],
        "form_signals": [],
    }
    if not snapshot:
        result["reasons"].append(
            "Piyasa snapshot'ı yok; Yahoo sıralaması veya kabul olasılığı türetilmedi."
        )
        return result
    try:
        source = snapshot["source"]
        stamp = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
        metric = snapshot["metric"]
        entries = snapshot["players"]
        if (
            not isinstance(source, str)
            or not source.strip()
            or stamp.tzinfo is None
            or metric not in ("rank", "replacement_adjusted_trade_value")
            or not isinstance(entries, dict)
        ):
            raise ValueError("Unsupported market source or metric")
    except (KeyError, TypeError, ValueError, AttributeError):
        result.update(
            status="invalid",
            reasons=["Piyasa kaynağı, zamanı, metriği veya oyuncu tablosu geçersiz."],
        )
        return result
    result.update(source=source, captured_at=stamp.isoformat(), metric=metric)
    age = context.as_of - stamp
    if age < -timedelta(minutes=5) or age > timedelta(days=max_age):
        result.update(
            status="stale",
            reasons=["Piyasa snapshot'ı gelecek tarihli veya izin verilen yaştan eski."],
        )
        return result
    sides = [[str(i) for i in proposal[key]] for key in ("give_yahoo_ids", "receive_yahoo_ids")]
    records = [[entries.get(i, {}) for i in ids] for ids in sides]
    if any(not isinstance(r, dict) for side in records for r in side):
        result.update(status="invalid", reasons=["Oyuncu piyasa kaydı sözlük olmalı."])
        return result
    complete_ranks = all(
        _number(r.get("rank"), True) and type(r["rank"]) is int for side in records for r in side
    )
    if complete_ranks:
        best = [min(r["rank"] for r in side) for side in records]
        result["best_rank"] = {"give": best[0], "receive": best[1]}
        if (metric == "rank" or min(best) <= elite) and abs(best[0] - best[1]) > rank_gap:
            result["blocked"] = True
            result["reasons"].append(
                "İki paketin en iyi kaynaklı piyasa sıraları arasındaki fark politika sınırının üzerinde."
            )
    for ids, side in zip(sides, records):
        for yahoo_id, record in zip(ids, side):
            projected = record.get("projected_rank")
            if not _number(projected, True):
                continue
            pid = context.yahoo_ids.get(yahoo_id)
            name = context.engine.players[pid].name if pid in context.engine.players else yahoo_id
            for period in (14, 30):
                recent = record.get(f"recent_rank_{period}d")
                if _number(recent, True) and abs(recent - projected) >= 20:
                    result["form_signals"].append(
                        {
                            "name": name,
                            "days": period,
                            "recent_rank": recent,
                            "projected_rank": projected,
                            "signal": "recent_weaker" if recent > projected else "recent_stronger",
                        }
                    )
    if metric == "replacement_adjusted_trade_value":
        if not all(_number(r.get("trade_value")) for side in records for r in side):
            result["status"] = "incomplete"
            result["reasons"].append(
                "Paketin her oyuncusu için aynı ölçekte replacement-adjusted trade_value gerekli."
            )
        else:
            totals = [sum(r["trade_value"] for r in side) for side in records]
            if not all(math.isfinite(t) for t in totals):
                result.update(status="invalid", reasons=["Piyasa değer toplamları sonlu olmalı."])
                return result
            result["totals"] = {"give": totals[0], "receive": totals[1]}
            if max(totals) == 0:
                result["status"] = "uninformative"
                result["reasons"].append(
                    "İki paketin de piyasa değeri sıfır; makullük doğrulanamadı."
                )
            else:
                ratio = max(totals) / min(totals) if min(totals) else None
                finite_ratio = ratio is not None and math.isfinite(ratio)
                result["value_ratio"] = ratio if finite_ratio else None
                if not finite_ratio or ratio > max_ratio:
                    result["blocked"] = True
                    result["reasons"].append(
                        "Kaynaklı piyasa değerleri yapılandırılmış denge sınırının dışında."
                    )
                result["status"] = "balanced_value"
                result["requires_review"] = False
    else:
        result["status"] = "rank_screen_only" if complete_ranks else "incomplete"
        result["reasons"].append(
            "Sıralar toplanmadı; ordinal sıra kontrolü bütün paketin fiyatını doğrulamaz."
        )
    if result["blocked"]:
        result.update(status="outlier", requires_review=True)
    return result
