"""Short HTML notification; the detailed tables stay in the report."""

import hashlib
from collections.abc import Mapping
from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo


class DeliveryError(RuntimeError):
    def __init__(self, reason, receipts):
        super().__init__(reason)
        self.receipts = receipts


def send_telegram(token, chat, message, post=None):
    """Return API receipts; never expose token, chat ID or response payload."""
    if post is None:
        import requests

        post = requests.post
    chunks, lines, size = [], [], 0
    for line in message.splitlines():
        units = len((line + "\n").encode("utf-16-le")) // 2
        if units > 3800:
            raise DeliveryError("Single Telegram line exceeds safe limit", [])
        if size + units > 3800:
            chunks.append("\n".join(lines))
            lines, size = [], 0
        lines.append(line)
        size += units
    if lines:
        chunks.append("\n".join(lines))
    receipts = []
    for index, chunk in enumerate(chunks, 1):
        try:
            response = post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                timeout=12,
                json={
                    "chat_id": chat,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            payload = response.json()
            result = payload.get("result", {})
            if (
                response.status_code != 200
                or payload.get("ok") is not True
                or type(result.get("message_id")) is not int
            ):
                raise ValueError("API did not acknowledge message")
        except Exception as exc:
            raise DeliveryError(
                "Telegram delivery failed: " + type(exc).__name__, receipts
            ) from None
        receipts.append(
            {
                "part": index,
                "message_id": result["message_id"],
                "api_date": result.get("date"),
                "accepted_at": datetime.now(timezone.utc).isoformat(),
                "text_sha256": hashlib.sha256(chunk.encode()).hexdigest(),
            }
        )
    return receipts


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
    ownership_audit=None,
    live_score_block_reason=None,
):
    def label(category):
        return category.replace("_PCT", "%").replace("FG3M", "3PT")

    lines = [
        "🏀 <b>NBA Fantasy</b>",
        escape(now.astimezone(ZoneInfo("Europe/Berlin")).strftime("%d.%m · %H:%M %Z"))
        + " · "
        + escape(str(opponent)[:65]),
        "",
    ]
    if live:
        lines.append(
            f"<b>Beklenen kategori puanı: {points:.2f} / 9</b>"
            if objective == "category_points"
            else f"<b>Playoff ilerleme kredisi: {points:.1%}</b>"
        )
        if objective == "category_points":
            lines.append(
                "Kazanılan kategori 1, beraberlik ½ puan. Bu bir beklenti; kesin skor değil."
            )
    else:
        lines.extend(
            [
                f"<b>Kalan maçlar: {points:.2f} / 9 kategori puanı</b>",
                "Canlı skor doğrulanmadı; hafta sonu skoru değildir.",
            ]
        )
    lines.extend(["", "<b>Haftalık maçlar · oynanan / toplam</b>"])

    def games(team):
        try:
            played, total, remaining = [
                int(team[k]) for k in ("games_played", "total_scheduled", "games_remaining")
            ]
            if min(played, total, remaining) < 0 or played + remaining != total:
                return "Kaynak maç sayıları tutarsız"
            return f"{played} / {total} oynandı · {remaining} kalan"
        except (KeyError, TypeError, ValueError):
            return "Maç sayısı bilgisi yok"

    snapshot = live if isinstance(live, Mapping) else {}
    lines.append("Sen: " + games(snapshot.get("team_a", {})))
    lines.append("Rakip: " + games(snapshot.get("team_b", {})))
    lines.extend(["", "<b>Kategori kazanma ihtimalleri</b>"])
    display_order = ["FG_PCT", "FT_PCT", "FG3M", "PTS", "REB", "AST", "STL", "BLK", "TOV"]
    ordered = [c for c in display_order if c in probabilities] + sorted(
        set(probabilities) - set(display_order)
    )
    items = [f"{label(c)} %{100 * probabilities[c]:.0f}" for c in ordered]
    lines.extend(" · ".join(items[i : i + 3]) for i in range(0, len(items), 3))
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
        reason = str(live_score_block_reason or "")
        if "different synchronization" in reason:
            lines.append(
                "Kadro yenilendi, skor aynı senkronizasyonda alınamadı. Hamle önerileri bekletiliyor."
            )
        elif "games have started" in reason:
            lines.append(
                "NBA maçları başladı; kısmi skorun kalan süresi doğrulanamadığı için hamleler bekletiliyor."
            )
        elif "clock" in reason.lower() or "tipoff" in reason.lower():
            lines.append("Kesin NBA maç saati kaydı doğrulanamadı; hamleler bekletiliyor.")
        elif "Eastern game date" in reason or "stale" in reason.lower():
            lines.append("Skor güncel Eastern oyun gününe ait değil; hamleler bekletiliyor.")
        elif "identity invalid" in reason or "exceed" in reason:
            lines.append(
                "Skor sütunları birbiriyle tutarlı değil; hatalı tabloyla hamle önerilmedi."
            )
        else:
            lines.append("Canlı skor güncellenene kadar öneriler bekletiliyor.")
    elif ownership_audit and ownership_audit.get("reason"):
        lines.append(
            "Güncel Yahoo boşta oyuncu listesi doğrulanmadı; hamle önerileri bekletiliyor. Yahoo senkronizasyonunu yenile."
        )
    elif not moves:
        lines.append("Belirgin kazanç sağlayan bir hamle görünmüyor.")
    for rank, row in enumerate(moves[:6], 1):
        delta = row["delta_objective_value"]
        baseline = row.get("base_objective_value", points)
        after = row.get("new_objective_value", baseline + delta)
        drop = (
            "Boş yere ekle"
            if row.get("drop_id") is None
            else "Bırak: " + escape(str(row["drop_name"])[:55])
        )
        lines.extend(["", f"<b>{rank}. Al: {escape(str(row['add_name'])[:55])}</b> · {drop}"])
        if objective == "category_points":
            lines.append(f"Beklenen kategori puanı: {baseline:.2f} → {after:.2f} (+{delta:.3f})")
        else:
            lines.append(f"Playoff ilerleme kredisi: %{baseline * 100:.1f} → %{after * 100:.1f}")
        gp = row.get("observed_games", 0)
        if gp:
            lines.append(
                f"Gözlem: {gp} maç · {row['observed_minutes']:.1f} dk/maç | Model: {row.get('projected_minutes', row['observed_minutes']):.1f} dk"
            )
            uplift = row.get("projected_minutes", 0) - row.get("role_base_minutes", 0)
            if uplift >= 0.5:
                lines.append(
                    f"Sakatlık/rotasyon varsayımı: +{uplift:.1f} dk; doğrulanmış süre artışı değil."
                )
        pg = row.get("exp_stats_pg", {})
        if all(s in pg for s in ("PTS", "REB", "AST")):
            lines.append(
                f"Model/maç: {pg['PTS']:.1f} sayı · {pg['REB']:.1f} rib · {pg['AST']:.1f} ast"
            )
        details = row.get("cat_details", [])[:2]
        if details:
            lines.append(
                " · ".join(f"{label(d['cat'])} %{d['base_pct']} → %{d['new_pct']}" for d in details)
            )
        if "rem_games_add" in row:
            lines.append(
                f"Kalan NBA maçı: {row['rem_games_add']:g} · Kadro yoğunluğuna göre bazıları oynatılamayabilir."
            )
    if len(moves) > 1:
        lines.extend(["", "Hamleler birbirinin alternatifidir; kazançları toplanmaz."])
    if provisional:
        lines.extend(
            ["", "<i>Dakika güncellemesi geçici kabulde; eski yöntem paralel izleniyor.</i>"]
        )
    lines.extend(["", "Ayrıntılar: GitHub Actions raporu"])
    return "\n".join(lines)
