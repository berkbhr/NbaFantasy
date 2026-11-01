"""Turkish Markdown presentation of one immutable trade evaluation."""

import re
from html import escape


def _md(value):
    text = escape(str(value), quote=False).replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|])", r"\\\1", text)


def playoff_team_probabilities(row):
    """Accept the qualification engine's paired-MC schema and monitor schema."""
    return (
        row.get("before_probability", row.get("before")),
        row.get("after_probability", row.get("after")),
        row.get("delta_probability", row.get("delta")),
        row.get("delta_mc_standard_error", row.get("mc_standard_error")),
    )


def playoff_report_lines(impact, team_names=None):
    """Qualification probabilities, separately from package/category value."""
    if not impact:
        return []
    lines = ["", "### Playoff'a katılım etkisi", ""]
    if impact.get("status") not in ("ready", "conditional_estimate"):
        lines.append(
            "Hesaplanamadı: gerçek puan durumu, kalan eşleşmeler veya güncel hafta verisi eksik/doğrulanmamış."
        )
        lines.extend("- " + _md(reason) for reason in impact.get("reasons", []))
        return lines
    lines += [
        "Koşullu tahmin; sabit kadrolar varsayılır. Streaming planının playoff etkisi bu hesaba dahil değildir.",
        "",
        "| Takım | Takassız | Takaslı | Değişim | Δ MC standart hata |",
        "|---|---:|---:|---:|---:|",
    ]
    for team, row in impact.get("teams", {}).items():
        label = _md((team_names or {}).get(str(team), f"Takım {team}"))
        before, after, delta, standard_error = playoff_team_probabilities(row)
        se = f"{100 * standard_error:.3f} yüzde puan" if standard_error is not None else "—"
        lines.append(
            f"| {label} | {before:.1%} | {after:.1%} | {100 * delta:+.2f} yüzde puan | {se} |"
        )
        sensitivity = (
            impact.get("variants", {}).get("without_spillover", {}).get("teams", {}).get(str(team))
        )
        if sensitivity:
            _, _, alternate_delta, _ = playoff_team_probabilities(sensitivity)
            lines.append(
                f"Sakatlık kaynaklı takım arkadaşı katkısı kapalıyken {label}: Δ {100 * alternate_delta:+.2f} yüzde puan."
            )
            if delta * alternate_delta < 0:
                lines.append(
                    "Senaryo değişince playoff etkisinin yönü değişiyor; güçlü olumlu sonuç çıkarılmamalı."
                )
    lines.append(
        "Monte Carlo örnekleme hatası model, sakatlık ve beraberlik bozma varsayımlarındaki hatayı kapsamaz."
    )
    lines.extend("- " + _md(reason) for reason in impact.get("assumptions", []))
    return lines


def render_trade_monitor(result):
    """Current imported pending offers only; never emits a Yahoo action link."""
    lines = ["## Bekleyen Yahoo takas teklifleri", ""]
    status = result.get("status")
    if status == "disabled":
        return "\n".join(lines + ["Takas izlemesi kapalı."]) + "\n"
    if status not in ("analyzed", "partial", "no_pending_offers"):
        lines.append(
            "Güncel teklif verisi doğrulanamadı; eski sonuçlar güncel öneri olarak gösterilmedi."
        )
        lines.extend("- " + _md(reason) for reason in result.get("reasons", []))
        return "\n".join(lines) + "\n"
    if result.get("captured_at"):
        lines.append("Yahoo teklif kaydı: " + _md(result["captured_at"]))
    lines += [
        "Politika: gelen/bekleyen gerçek teklifler; bu raporda geniş fırsat taraması çalıştırılmaz.",
        "",
    ]
    if status == "no_pending_offers":
        return "\n".join(lines + ["Doğrulanmış kayıtta bekleyen teklif yok."]) + "\n"
    labels = {
        "conditional_accept": "Koşullu kabul",
        "reject_suggested": "Ret değerlendirmesi",
        "counter_or_review": "Karşı teklif / inceleme",
        "borderline": "Sınırda",
        "needs_data": "Veri eksik",
    }
    for offer in result.get("offers", []):
        display = offer.get("display", {})
        lines += ["### Teklif " + _md(offer.get("offer_id", "—")), ""]
        lines.append("Durum: " + _md(offer.get("status", "bilinmiyor")))
        if display:
            lines += [
                _md(display.get("our_team", "Bizim takım"))
                + " ↔ "
                + _md(display.get("other_team", "Karşı takım")),
                "Verilen: " + ", ".join(_md(name) for name in display.get("give", [])),
                "Alınan: " + ", ".join(_md(name) for name in display.get("receive", [])),
            ]
        analysis = offer.get("analysis") or {}
        if offer.get("analysis_status") == "evaluated" and analysis:
            lines.append(
                "Değerlendirme: " + labels.get(analysis.get("verdict"), "Koşullu inceleme")
            )
            decision = analysis.get("decision", {})
            if decision.get("delta") is not None:
                lines.append(
                    f"Beklenen kategori puanı değişimi: {decision['delta']:+.3f} ({_md(decision.get('basis', ''))})."
                )
            bilateral = offer.get("bilateral", {})
            if bilateral.get("partner_conservative") is not None:
                lines.append(
                    f"Karşı takımın muhafazakâr kategori katkısı: {bilateral['partner_conservative']:+.3f}; menajerin kabul olasılığı değildir."
                )
            if offer.get("market", {}).get("requires_review"):
                lines.append("Piyasa doğrulaması gerekiyor.")
            lines.extend(
                playoff_report_lines(offer.get("playoff_impact"), analysis.get("team_names"))
            )
        else:
            lines.append("Analiz bekliyor / veri eksik; kabul veya ret sonucu üretilmedi.")
        lines.extend(
            "- " + _md(reason) for reason in offer.get("conditions", []) + offer.get("errors", [])
        )
        lines.append("")
    lines.append(
        "Sonuçlar karar desteğidir; Yahoo'da teklif gönderme, kabul veya ret işlemi yapılmaz."
    )
    return "\n".join(lines) + "\n"


def render_trade_report(result):
    if result.get("kind") == "three_team":
        from .trade_multiteam import render_multiteam_report

        return render_multiteam_report(result)

    team_names = result.get("team_names", {})

    def team_name(team):
        return team_names.get(str(team), f"Takım {team}")

    labels = {
        "borderline": "Sınırda",
        "counter_or_review": "Karşı teklif / inceleme",
        "reject_suggested": "Ret önerisi",
        "conditional_accept": "Koşullu kabul",
        "needs_data": "Veri eksik — ek inceleme gerekiyor",
    }
    lines = [
        "# Takas analizi",
        "",
        f"Veri anı: {result['as_of']}",
        f"Karar: **{labels[result['verdict']]}**",
        "Kapsam: "
        + {
            "remaining_full_regular_season_weeks": "Kalan normal sezonun tam gelecek haftaları",
            "supplied_weeks_only": "Yalnızca sağlanan haftalar",
        }.get(result["coverage"], result["coverage"]),
        "",
    ]
    if result.get("calendar_source"):
        source = result["calendar_source"]
        lines += [
            f"Fantasy fikstürü kaynağı: `{source['source']}`"
            + (f" ({source['season']})" if source.get("season") else "")
            + ".",
            "",
        ]
    proposal = result.get("proposal_display")
    if proposal:
        lines += [
            f"**{proposal['our_team']} ↔ {proposal['other_team']}**",
            "",
            f"{proposal['our_team']} veriyor: **{', '.join(proposal['give'])}**",
            "",
            f"{proposal['our_team']} alıyor: **{', '.join(proposal['receive'])}**",
            "",
            f"Yürürlük tarihi: {proposal['effective_date']}",
            "",
        ]
    names = result.get("names", {})

    def player_names(ids):
        return ", ".join(names[str(p)] for p in ids) or "Yok"

    decision = result.get("decision", {})
    if decision.get("basis") == "trade_plus_fa":
        lines += [
            "Kararın referansı: **takas + aşağıda adı verilen FA eklemesi**; "
            "aynı FA havuzunu kullanabilen takassız kadroyla karşılaştırıldı.",
            "",
        ]
    elif decision.get("basis") == "trade_plus_streaming":
        lines += [
            "Kararın referansı: **takaslı ve takassız kadroların ayrı streaming planları**; "
            "aynı FA havuzu, koruma ve haftalık hamle kurallarıyla karşılaştırıldı.",
            "",
        ]
    elif decision.get("basis") == "trade_plus_joint_fa":
        lines += [
            "Kararın referansı: **bizim kadro yönetimimiz + karşı takımın tek FA tamamlaması**.",
            "",
        ]
    if result.get("roster_capacity"):
        lines += [
            "| Takım | Takas öncesi aktif/bench | Saf takas sonrası | Açık yer önce → sonra |",
            "|---|---:|---:|---:|",
        ]
        for team, capacity in result["roster_capacity"].items():
            lines.append(
                f"| {team_name(team)} | {capacity['before_active']} | {capacity['after_active']} | "
                f"{capacity['before_open']} → {capacity['after_open']} |"
            )
        lines.append("")
    actions = result.get("roster_actions", {})
    if any(actions.get("drops", {}).values()):
        lines += ["## Zorunlu kadro düzenlemesi", ""]
        for team, ids in actions["drops"].items():
            if ids:
                lines += [f"{team_name(team)} bırakıyor: **{player_names(ids)}**", ""]
        lines += ["Aşağıdaki saf takas sonuçları bu bırakmaların maliyetini içerir.", ""]
    if any(actions.get("post_trade_il", {}).values()):
        lines += ["İşlem sonrası IL yerleşimi:", ""]
        for team, ids in actions["post_trade_il"].items():
            lines.append(f"- {team_name(team)}: {player_names(ids)}")
        lines.append("")
    for team, values in result["teams"].items():
        total = values["all_supplied_weeks"]
        lines += [
            f"## {team_name(team)} — saf takas ve zorunlu bırakmalar",
            "",
            f"Beklenen kategori puanı ({total['weeks']} hafta): "
            f"{total['before']:.3f} → {total['after']:.3f} (Δ {total['delta']:+.3f})",
            f"İlk dört sağlanan hafta: Δ {values['near_term']['delta']:+.3f}",
            f"Sakatlık dakika dağıtımı kapalı: Δ {values['without_spillover_delta']:+.3f}",
            "",
            "| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |",
            "|---|---:|---:|---:|---:|",
        ]
        for cat, row in total["categories"].items():
            lines.append(
                f"| {cat} | %{100 * row['before_win']:.2f} | %{100 * row['after_win']:.2f} | "
                f"{100 * (row['after_win'] - row['before_win']):+.2f} | {row['delta_points']:+.3f} |"
            )
        lines += ["", "### Haftalık üretim ve rakip", ""]
        for week in values["weekly"]:
            lines += [
                f"{week['start']} – {week['end']}, rakip: {team_name(week['opponent'])}",
                "",
                "| Kategori | Önce üretim | Sonra üretim |",
                "|---|---:|---:|",
            ]
            for cat, row in week["before"]["categories"].items():
                after = week["after"]["categories"][cat]["production"]
                lines.append(f"| {cat} | {row['production']:.3f} | {after:.3f} |")
            lines.append("")
    completion = result.get("completion", {})
    if completion.get("status") not in (None, "disabled", "no_new_open_slot"):
        lines += ["## Boşalan yer için FA seçenekleri", ""]
        for team, counts in completion.get("search", {}).get("teams", {}).items():
            lines += [
                f"{team_name(team)}: tarih ve bütçesi uygun {counts['eligible']} adaydan "
                f"{counts['evaluated']} oyuncu tam motorla incelendi.",
                "",
            ]
        if not completion.get("options"):
            lines += [
                "Doğrulanmış bütçeyle anlamlı ek katkı sağlayan bir seçenek sunulmadı.",
                "",
            ]
        for option in completion.get("options", []):
            team = option["team"]
            lines += [
                f"### {team_name(team)}: {option['name']}",
                "",
                f"Ekleme günü: {option['date']} · Yahoo durumu: {option['status']}",
                "",
                f"İncelenen takassız referans: {option['baseline_category_points']:.3f}; "
                f"takas + FA: {option['after_category_points']:.3f} kategori puanı.",
                "",
                f"Adil referansa göre Δ: **{option['delta']:+.3f}**; sakatlık dakika dağıtımı "
                f"kapalı: {option['delta_without_spillover']:+.3f}. "
                f"Saf takasa ek katkı: {option['extra_over_trade_only']:+.3f}.",
                "",
            ]
            baseline_add = option.get("baseline_actions")
            if baseline_add:
                lines += [
                    f"Takassız referans ekliyor: {names[str(baseline_add['player_id'])]} "
                    f"({baseline_add['date']}); bırakıyor: {player_names(option['baseline_drops'])}.",
                    "",
                ]
            else:
                lines += ["Takassız referans mevcut kadrosunu koruyor.", ""]
            lines += ["| Kategori | Adil referansa göre Δ kategori puanı |", "|---|---:|"]
            for cat, row in option["teams"][team]["all_supplied_weeks"]["categories"].items():
                lines.append(f"| {cat} | {row['delta_points']:+.3f} |")
            lines.append("")
        if "threshold_points" in completion:
            lines += [
                f"Anlamlılık eşiği: haftada {completion['min_gain_per_week']:.3f} "
                "kategori puanı; bu bir karar ayarıdır, kalibre edilmiş güven ölçüsü değildir.",
                "",
            ]
        lines += [f"- {reason}" for reason in completion.get("reasons", [])]
        lines.append("")
    streaming = result.get("streaming", {})
    if streaming.get("status") not in (None, "disabled"):
        lines += ["## Streaming: tarihli kadro ve hamle planı", ""]
        if streaming.get("status") == "planned":
            lines += [
                f"Yönetilen takassız kadroya göre Δ: **{streaming['delta']:+.3f}**; "
                f"sakatlık dakika dağıtımı kapalı: {streaming['delta_without_spillover']:+.3f}.",
                "",
                f"Takaslı kadroda streaming'in saf takasa ek katkısı: "
                f"{streaming['extra_over_trade_only']:+.3f} kategori puanı.",
                "",
            ]
            for key, label in (("before", "Takassız kadro"), ("after", "Takaslı kadro")):
                plan = streaming[key]
                lines += [f"### {label}", ""]
                if plan["actions"]:
                    lines += [
                        "| Tarih | Alınacak oyuncu | Bırakılacak oyuncu |",
                        "|---|---|---|",
                    ]
                    for action in plan["actions"]:
                        dropped = (
                            "Yok — boş yer kullanılıyor"
                            if action.get("drop_id") is None
                            else names[str(action["drop_id"])]
                        )
                        lines.append(
                            f"| {action['date']} | {names[str(action['add_id'])]} | {dropped} |"
                        )
                else:
                    lines.append("Hamle yok; kadro korunuyor.")
                lines += [
                    "",
                    "| Hafta başlangıcı | Limit | Önceden kullanılan | Takas maliyeti | Planlanan ekleme | Kalan |",
                    "|---|---:|---:|---:|---:|---:|",
                ]
                for week, budget in plan["weekly_budget"].items():
                    used = (
                        budget["used_before"] if budget["used_before"] is not None else "Bilinmiyor"
                    )
                    remaining = (
                        budget["remaining"] if budget["remaining"] is not None else "Bilinmiyor"
                    )
                    lines.append(
                        f"| {week} | {budget['limit']} | {used} | {budget['trade_cost']} | "
                        f"{budget['planned_adds']} | {remaining} |"
                    )
                lines += ["", f"Son kadro: {player_names(plan['final_roster'])}", ""]
            our_team = str(result["proposal"]["our_team"])
            lines += [
                "| Kategori | İki streaming planı arasında Δ kategori puanı |",
                "|---|---:|",
            ]
            for cat, row in streaming["teams"][our_team]["all_supplied_weeks"][
                "categories"
            ].items():
                lines.append(f"| {cat} | {row['delta_points']:+.3f} |")
            lines.append("")
            search = streaming.get("search", {})
            lines += [
                f"Arama sınırları: {search.get('candidate_count', 0)} aday, "
                f"beam genişliği {search.get('beam_width', 0)}, "
                f"son değerlendirme bütçesi {search.get('finalists', 0)}. "
                "Arama yaklaşık sonuç verir; global optimum garantisi yoktur.",
                "",
            ]
        else:
            lines += [
                "Streaming planı için gerekli veri sağlanamadı; karar mevcut analizle sınırlı.",
                "",
            ]
        lines += [f"- {message}" for message in streaming.get("conditions", [])]
        lines.append("")
    partner = result.get("partner_completion", {})
    if partner.get("status") == "applied":
        option = partner["options"][0]
        lines += [
            "## Karşı takımın tek FA tamamlaması",
            "",
            f"{team_name(partner['team'])}, {option['date']} tarihinde **{option['name']}** alır.",
            "",
            "Bu karşılaştırma bizim mevcut yönetim planıyla birlikte hesaplanır; "
            "aynı FA iki takıma atanmaz.",
            "",
        ]
        for team, summary in partner["teams"].items():
            lines.append(
                f"- {team_name(team)}: nihai Δ {summary['all_supplied_weeks']['delta']:+.3f} kategori puanı."
            )
        lines.append("")
    lines += [
        "## Eşit maç hacminde paket üretimi",
        "",
        result["normalized_package"]["definition"],
        "",
        "| İstatistik | Verilen | Alınan | Δ |",
        "|---|---:|---:|---:|",
    ]
    neutral = result["normalized_package"]
    for cat, delta in neutral["delta"].items():
        lines.append(
            f"| {cat} | {neutral['outgoing'][cat]:.3f} | "
            f"{neutral['incoming'][cat]:.3f} | {delta:+.3f} |"
        )
    lines += ["", "## Playoff takvimi: ham NBA maç sayısı", ""]
    if not result["playoff_schedule"]:
        lines.append("Doğrulanmış playoff tarihleri girilmedi.")
    for period in result["playoff_schedule"]:
        lines.append(f"{period['start']} – {period['end']}")
        for pid, games in period["scheduled_games"].items():
            lines.append(
                f"- {result['names'][pid]}: {games} maç (aktif kadroya sığma garantisi yok)"
            )
    lines.extend(playoff_report_lines(result.get("playoff_impact"), team_names))
    lines += ["", "## Koşullar ve varsayımlar", ""]
    lines += [f"- {message}" for message in result["conditions"] + result["assumptions"]]
    return "\n".join(lines) + "\n"
