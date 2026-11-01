"""Main-model category outlook against the actual remaining fantasy opponents."""

import copy

import pandas as pd

from .probability import category_points


def build_future_outlook(engine, rosters, team, calendar, as_of, team_names=None):
    result = {k: copy.deepcopy(v) for k, v in calendar.items() if k != "weeks"}
    result.update(
        weeks=[],
        objective="category_points",
        assumptions=[
            "Current rosters held fixed; no future acquisitions or trades assumed.",
            "Availability/roles use today's information; distant weeks are conditional projections.",
            "No playoff qualification probability: standings and tiebreaks are not modeled here.",
        ],
    )
    if not calendar.get("weeks"):
        return result
    rosters = {str(k): list(v) for k, v in rosters.items()}
    team = str(team)
    model = copy.deepcopy(engine)
    model.objective, model.draw_value = "category_points", 0.5
    # Keep observed IL placement. Do not create future IL moves automatically.
    model.yahoo_il_eligible_ids = set()
    as_of_day = pd.Timestamp(as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    last_nba_day = (
        pd.to_datetime(model.schedule.GAME_DATE).max() if not model.schedule.empty else pd.NaT
    )
    for week in calendar["weeks"]:
        if pd.isna(last_nba_day) or pd.Timestamp(week["end"]) > last_nba_day:
            result.update(
                status="partial",
                complete_remaining_season=False,
                reason="Future fantasy dates exceed cached NBA schedule coverage",
            )
            break
        opponent = next(
            (
                str(b) if str(a) == team else str(a)
                for a, b in week["fixtures"]
                if team in (str(a), str(b))
            ),
            None,
        )
        if opponent not in rosters or team not in rosters:
            result.update(
                status="unavailable", reason="A scheduled team has no live roster", weeks=[]
            )
            return result
        if any(model.team_map.get(p) is None for p in rosters[team] + rosters[opponent]):
            result.update(
                status="partial",
                complete_remaining_season=False,
                reason="Scheduled roster contains a player with unknown NBA team",
            )
            break
        _, _, _, probabilities, _ = model.project_matchup(
            rosters[team],
            rosters[opponent],
            week["start"],
            week["end"],
            as_of_date=as_of_day,
        )
        result["weeks"].append(
            {
                "week": week["week"],
                "start": week["start"],
                "end": week["end"],
                "opponent": opponent,
                "opponent_name": (team_names or {}).get(opponent, opponent),
                "captured_at": week["captured_at"],
                "source": week.get("source", calendar["source"]),
                "expected_category_points": category_points(probabilities),
                "categories": {
                    c: {
                        "win": p,
                        "tie": probabilities.ties[c],
                        "points": p + 0.5 * probabilities.ties[c],
                    }
                    for c, p in probabilities.items()
                },
            }
        )
    rows = result["weeks"]
    if rows:
        result["aggregate"] = {
            "weeks": len(rows),
            "expected_category_points": sum(r["expected_category_points"] for r in rows),
            "average_category_points": sum(r["expected_category_points"] for r in rows) / len(rows),
            "categories": {
                c: sum(r["categories"][c]["points"] for r in rows) / len(rows)
                for c in rows[0]["categories"]
            },
        }
        near = rows[:4]
        result["next_four_full_weeks"] = {
            "weeks": len(near),
            "expected_category_points": sum(r["expected_category_points"] for r in near),
        }
        result["opponent_frequency"] = {
            opponent: sum(r["opponent"] == opponent for r in rows)
            for opponent in sorted({r["opponent"] for r in rows})
        }
    return result


def report_lines(outlook):
    lines = ["", "## Gelecek fantasy fikstürüne göre kategori görünümü", ""]
    if not outlook.get("weeks"):
        return lines + [
            "Hesaplanamadı: "
            + str(outlook.get("reason") or outlook.get("status", "unavailable"))
            + "."
        ]
    aggregate = outlook["aggregate"]
    scope = (
        "Kalan normal sezonun tamamı"
        if outlook.get("complete_remaining_season")
        else "Doğrulanmış/istenen haftalar; kalan sezonun tamamı değil"
    )
    lines += [
        f"{scope}: {aggregate['weeks']} tam hafta. Kaynak: `{', '.join(outlook.get('sources') or [outlook['source']])}` ({outlook['season']}).",
        f"Beklenen kategori puanı: **{aggregate['expected_category_points']:.3f} / {9 * aggregate['weeks']}**; hafta başına **{aggregate['average_category_points']:.3f} / 9**.",
        "Mevcut haftanın kalan kısmı üstteki canlı hesapta ayrı değerlendirilir. Güncel kadrolar sabit tutulur; gelecek FA/streaming hamleleri varsayılmaz.",
        "",
        "| Hafta | Tarihler | Gerçek fantasy rakibi | Beklenen kategori puanı |",
        "|---|---|---|---:|",
    ]
    for week in outlook["weeks"]:
        name = week["opponent_name"].replace("|", "\\|")
        lines.append(
            f"| {week['week']} | {week['start']} – {week['end']} | {name} | {week['expected_category_points']:.3f} / 9 |"
        )
    lines += [
        "",
        "Kategori başına ortalama P(kazanma) + 0.5 × P(beraberlik): "
        + "; ".join(f"{c}: {p:.1%}" for c, p in aggregate["categories"].items())
        + ".",
    ]
    if outlook.get("reason"):
        lines += ["Kapsam koşulu: " + outlook["reason"]]
    lines += ["Bunlar koşullu kadro projeksiyonlarıdır; playoff'a katılım olasılığı değildir."]
    return lines
