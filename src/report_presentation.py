"""Panel presentation of the existing Telegram snapshot policy; no model calculations."""

from copy import deepcopy

from .notification_state import notification_snapshot

PREDICTION_FIELDS = (
    "objective_value",
    "expected_category_points",
    "expected_category_wins",
    "expected_category_ties",
    "win",
    "draw",
    "loss",
)


def block_explanation(reason):
    if "games have started" in str(reason):
        return (
            "Bugünün NBA maçları başladı. Model, sürmekte olan maçların kalan bölümünü "
            "ayrı hesaplayamadığı için haftalık tahmini durdurdu. Canlı skora tam maç "
            "tahmini ekleyip aynı üretimi iki kez saymamak için olasılıklar gösterilmiyor."
        )
    return "Haftalık tahmin doğrulanamadı. " + str(reason or "Güncel Yahoo skor kaydı gerekli.")


def game_rows(board):
    """Provider-observed game counts, never inferred from model lineups."""
    rows = []
    for key, label in (("team_a", "Sen"), ("team_b", "Rakip")):
        team = (board or {}).get(key, {})
        row = {"side": label, "valid": False}
        try:
            values = [team[k] for k in ("games_played", "total_scheduled", "games_remaining")]
            counts = [int(v) for v in values]
            if any(isinstance(v, bool) or float(v) != n for v, n in zip(values, counts)):
                raise ValueError("Non-integral game count")
            played, total, remaining = counts
            if min(counts) < 0 or played + remaining != total:
                raise ValueError("Inconsistent provider counts")
            row.update(valid=True, played=played, total=total, remaining=remaining)
        except (KeyError, ValueError, TypeError, OverflowError):
            pass
        rows.append(row)
    return rows


def present_forecast(current, archive, panel_archive=None):
    """Match Telegram's validated/current/archive/blocked decision exactly.

    Invalid raw predictions remain untouched on disk and in the model result.
    They must never appear as weekly forecasts in this UI or its Excel export.
    """
    selected, context = notification_snapshot(current, archive)
    if panel_archive is not None and not current.get("live_score_valid"):
        candidate, candidate_context = notification_snapshot(current, panel_archive)
        if candidate_context and (
            context is None or candidate["forecast_at"] > selected["forecast_at"]
        ):
            selected, context = candidate, candidate_context
    report = deepcopy(selected)
    available = bool(report.get("live_score_valid") and report.get("live_score"))
    mode = "last_valid_forecast" if available and context else "valid" if available else "blocked"
    report["display_mode"] = mode
    report["weekly_forecast_available"] = available
    report["display_context"] = deepcopy(context)
    report["evaluated_at"] = current.get("forecast_at")
    reason = current.get("live_score_block_reason")
    report["display_message"] = (
        "Son geçerli tahmin gösteriliyor; güncel canlı tahmin değildir. Hamleler kullanılamaz. "
        + block_explanation(reason)
        if mode == "last_valid_forecast"
        else block_explanation(reason)
        if not available
        else ""
    )
    board = current.get("live_score") or current.get("verified_scoreboard")
    report["game_counts"] = game_rows(board)
    report["game_counts_at"] = current.get("forecast_at")
    report["game_counts_basis"] = (
        "Son doğrulanan Yahoo skor kaydı; modelin aktif kadro sayısı değildir."
    )
    report["forecast_game_counts"] = game_rows(report.get("live_score")) if context else []
    if mode != "valid":
        # Archived moves are no more actionable here than in render_telegram.
        report["recommendations"] = []
    if not available:
        for key in PREDICTION_FIELDS:
            report[key] = None
        for key in (
            "categories",
            "my_projected_stats",
            "opponent_projected_stats",
            "my_lineups",
            "category_diagnostics",
        ):
            report[key] = {}
    return report
