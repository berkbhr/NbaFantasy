"""Short HTML notification; the detailed tables stay in the report."""

from html import escape


def render_preview(message):
    return (
        '<!doctype html><html lang="tr"><meta charset="utf-8">'
        '<title>Telegram önizleme</title><body style="margin:40px auto;max-width:430px;'
        "padding:24px;font:16px/1.55 system-ui;background:#edf3f6;color:#182533;"
        'white-space:pre-line;border-radius:18px">' + message + "</body></html>"
    )


def render_telegram(
    *,
    now,
    opponent,
    points,
    probabilities,
    health,
    recommendations,
    live=None,
    objective="category_points",
    provisional=True,
):
    def label(category):
        return category.replace("_PCT", "%").replace("FG3M", "3PT")

    lines = [
        "🏀 <b>NBA Fantasy</b>",
        escape(now.strftime("%d.%m · %H:%M UTC")) + " · " + escape(str(opponent)[:65]),
        "",
    ]
    if live:
        lines.append(
            f"<b>Beklenen kategori puanı: {points:.2f} / 9</b>"
            if objective == "category_points"
            else f"<b>Playoff ilerleme kredisi: {points:.1%}</b>"
        )
    else:
        lines.extend(
            [
                f"<b>Kalan maçlar: {points:.2f} / 9 kategori puanı</b>",
                "Canlı skor doğrulanmadı; hafta sonu skoru değildir.",
            ]
        )
    ties = getattr(probabilities, "ties", {})
    critical = sorted(
        probabilities, key=lambda c: abs(probabilities[c] + 0.5 * ties.get(c, 0) - 0.5)
    )[:3]
    lines.append(
        "Yakın kategoriler · "
        + " · ".join(f"{label(c)} %{100 * probabilities[c]:.0f}" for c in critical)
    )
    lines.append("Yüzdeler kategori kazanma olasılığıdır.")
    alerts = [r for r in health if r.get("is_out") or r.get("eff_avail", 1) < 0.8]
    if alerts:
        lines.extend(["", "<b>Kadro uyarıları</b>"])
        for row in alerts[:4]:
            hint = " · IL+" if row.get("slot_state") == "IL+" else ""
            lines.append(f"• {escape(str(row['name'])[:55])} — {escape(str(row['status']))}{hint}")
        if len(alerts) > 4:
            lines.append(f"+{len(alerts) - 4} uyarı ayrıntılı raporda")
    lines.extend(["", "<b>Hamle seçenekleri</b>"])
    threshold = 0.035 if objective == "category_points" else 0.005
    moves = (
        [r for r in recommendations if r.get("delta_objective_value", 0) >= threshold]
        if live
        else []
    )
    if not live:
        lines.append("Canlı skor güncellenene kadar öneriler bekletiliyor.")
    elif not moves:
        lines.append("Belirgin kazanç sağlayan bir hamle görünmüyor.")
    for row in moves[:2]:
        unit = "kategori puanı" if objective == "category_points" else "ilerleme kredisi"
        lines.append(
            f"• Al: <b>{escape(str(row['add_name'])[:55])}</b>\n"
            f"  Bırak: {escape(str(row['drop_name'])[:55])} · +{row['delta_objective_value']:.3f} {unit}"
        )
    if len(moves) > 1:
        lines.append("Bunlar birbirinin alternatifidir.")
    if provisional:
        lines.extend(
            ["", "<i>Dakika güncellemesi geçici kabulde; eski yöntem paralel izleniyor.</i>"]
        )
    lines.extend(["", "Ayrıntılar: GitHub Actions raporu"])
    return "\n".join(lines)
