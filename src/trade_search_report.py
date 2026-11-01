"""Named, source-attributed presentation of bounded trade search results."""

from .trade_report import playoff_report_lines
from .trade_search import effective_team_summaries as _effective_summaries


def concise_conditions(conditions):
    """Keep material limits once, in Turkish; raw source notes remain in JSON."""
    output = []
    partial_pool = any("FA havuzu:" in text and "kısmi tarama" in text for text in conditions)
    translations = (
        (
            "Piyasa snapshot'ı yok",
            "Harici piyasa verisi doğrulanmadı; model sonucu menajerin kabul edeceği anlamına gelmez.",
        ),
        (
            "Piyasa makullüğü doğrulanmadı",
            "Harici piyasa verisi doğrulanmadı; model sonucu menajerin kabul edeceği anlamına gelmez.",
        ),
        (
            "usage is unknown",
            "Gelecek haftaların hamle tüketimi bilinmiyor; bu haftalarda FA/streaming eklemeleri yapılmadı.",
        ),
        (
            "Current player roles",
            "Gelecek üretim mevcut oyuncu rolleri ve sakatlık varsayımlarına dayanır.",
        ),
        (
            "Per-team capture times",
            "Kadro kaydı topludur; takımların ayrı okunma zamanları doğrulanamıyor.",
        ),
        (
            "eligibility is incomplete",
            "Bazı Yahoo pozisyon uygunlukları yaklaşık; günlük kadro sonuçları buna bağlıdır.",
        ),
        (
            "position eligibility is approximate",
            "Bazı Yahoo pozisyon uygunlukları yaklaşık; günlük kadro sonuçları buna bağlıdır.",
        ),
        ("Trade rules have not", "Lig takas kuralları henüz doğrulanmadı."),
        ("Fantasy fixtures have not", "Analizde kullanılan fantasy eşleşmeleri doğrulanmadı."),
        ("Refresh stale rosters", "Kadro kaydı eski; işlemden önce Yahoo senkronu yenilenmeli."),
        (
            "injury designation",
            "Sakat oyuncu içeren paketlerde dönüş tarihi varsayımı sonucu değiştirebilir.",
        ),
        (
            "Streaming uses bounded",
            "Streaming araması sınırlıdır; en iyi olası hamle dizisini bulma garantisi yoktur.",
        ),
        (
            "Future FA availability",
            "FA/waiver erişimi gelecekte değişebilir; hamle günü yeniden kontrol edilmelidir.",
        ),
        (
            "At most one atomic",
            "Streaming planı takım başına günde en fazla bir ekleme/bırakma içerir; bırakılan oyuncu aynı ufukta yeniden alınmaz.",
        ),
        (
            "IL placement stays fixed",
            "Analiz ufkunda IL yerleşimi sabit tutulur; gelecekteki aktivasyonlar planlanmaz.",
        ),
        (
            "Post-trade IL assignment",
            "Seçilen takas sonrası IL yerleşimi analiz boyunca sabit kabul edilir.",
        ),
        (
            "Supplied weeks do not",
            "Sonuç seçilen haftalara aittir; kalan sezonun tamamı için çıkarım yapılmaz.",
        ),
        (
            "Availability scan is partial",
            "FA havuzu kısmi; yalnız doğrulanmış oyuncular değerlendirilmiştir.",
        ),
        ("No verified, eligible FA", "Bu ufukta doğrulanmış, uygun FA adayı bulunamadı."),
        (
            "FA-assisted decision",
            "FA içeren sonuç yalnız raporda adı verilen ekleme ve hamle bütçesiyle geçerlidir.",
        ),
        (
            "Streaming-assisted decision",
            "Streaming içeren sonuç yalnız rapordaki tarihli hamle planıyla geçerlidir.",
        ),
        (
            "Joint comparison includes",
            "İki takımın FA tamamlamaları birlikte değerlendirilir; aynı FA iki tarafa atanmaz.",
        ),
        (
            "Benefit disappears without",
            "Kazanç, sakatlıktan doğan ek süre varsayımı kaldırıldığında kayboluyor.",
        ),
        ("Near-term and full-window", "Yakın dönem ve bütün analiz ufku sonuçları zıt yönde."),
        (
            "Open-slot completion data",
            "Açılan kadro yerinin FA/bütçe verisi eksik; kesin karar verilemez.",
        ),
        ("Controlled", "Kontrollü yazılım örneği; gerçek lig tavsiyesi değildir."),
    )
    for text in dict.fromkeys(conditions):
        if not text:
            continue
        if text.startswith("FA havuzu:"):
            note = text.split(". Kısmi havuz", 1)[0]
        elif "Availability scan is partial" in text and partial_pool:
            continue
        else:
            note = next(
                (translated for pattern, translated in translations if pattern in text), None
            )
            if note is None:
                note = (
                    text
                    if any(char in text for char in "çğıöşüÇĞİÖŞÜ")
                    else "Diğer teknik koşullar ayrıntılı JSON kaydında korunur."
                )
        if note not in output:
            output.append(note)
    return output


def render_search_report(result):
    names = result["team_names"]
    title = "Karşı teklif araması" if result["mode"] == "counter" else "Takas fırsatı taraması"
    counts = result["counts"]
    conditions = list(result.get("conditions", []))
    lines = [
        f"# {title}",
        "",
        f"Takım: **{names.get(result['our_team'], result['our_team'])}**",
        f"Veri anı: {result['as_of']}",
        "",
        f"{counts['generated_packages']} paket hızlı modelde ele alındı; "
        f"{counts['screen_evaluated']} paket streaming olmadan, "
        f"{counts['refined']} son aday nihai ayarlarla değerlendirildi.",
        "",
        f"Piyasa sınırına takılan hızlı aday: {counts['market_outliers_skipped']}.",
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
    if result.get("scenario_scope"):
        lines[6:6] = [f"> Kapsam: {result['scenario_scope']}", ""]
    if result["original_analysis"] is not None:
        original = result["original_analysis"]
        display = original["proposal_display"]
        lines += [
            "## Mevcut teklif",
            "",
            f"{display['our_team']} veriyor: **{', '.join(display['give'])}**; "
            f"alıyor: **{', '.join(display['receive'])}**.",
            "",
            f"Mevcut teklifin nihai katkısı: {original['decision']['delta']:+.3f} kategori puanı.",
            "",
        ]
        market = result["original_market"]
        lines += [f"Mevcut teklif piyasa kontrolü: {market['status']}", ""]
        conditions.extend(market["reasons"])
        conditions.extend(original.get("conditions", []))
        lines.append("")
    review = result.get("review_opportunities", [])
    if review:
        lines += [
            f"**Model açısından uygun, piyasa incelemesi gereken aday: {len(review)}.** Bunlar kaynaklı piyasa doğrulaması tamamlanmış fırsatlar değildir.",
            "",
        ]
    preliminary = result.get("preliminary_candidates", [])
    if not result["opportunities"] and not review and not preliminary:
        lines += [
            "Bütün eşikleri karşılayan bir fırsat bulunmadı. İncelenmeyen paketler için sonuç çıkarılmaz.",
            "",
        ]
    elif result["opportunities"]:
        lines += [f"Koşullu fırsat sayısı: **{len(result['opportunities'])}**.", ""]
    scope = result.get("search_scope", {})
    if scope:
        targets = ", ".join(names.get(t, t) for t in scope["target_teams"])
        outgoing = ", ".join(scope["outgoing_names"]) or "Kendi kadrosunun tamamı"
        lines += [f"Arama kapsamı: {targets}. Verilecek tam paket: **{outgoing}**.", ""]
        if scope.get("focused_exhaustive"):
            lines += [
                "Sabit paket ve tek hedef için bütün uygun karşı paketler streaming kapalı ön değerlendirmeye alındı; nihai streaming yalnız sınırlı adaylarda çalışır.",
                "",
            ]
    thresholds = result.get("thresholds")
    if thresholds:
        lines += [
            f"{thresholds['weeks']} haftalık eşikler: bizim katkımız en az +{thresholds['our_min_gain']:.3f}; karşı tarafın kaybı en fazla −{thresholds['partner_max_loss']:.3f} kategori puanı.",
            "",
        ]
        weeks = thresholds["weeks"]
        if weeks:
            lines += [
                f"Bu eşikler kullanıcı tercihidir, istatistiksel güven veya anlamlılık sınırı değildir. Bizim haftalık kazanç tercihi {thresholds['our_min_gain'] / weeks:.3f}; karşı taraf için haftalık kayıp toleransı {thresholds['partner_max_loss'] / weeks:.3f}. Toplam eşikler bu değerlerin {weeks} haftayla çarpımıdır.",
                "",
            ]
    diagnostics = result.get("search_diagnostics", {})
    if diagnostics:
        lines += [
            f"Ön değerlendirmede model eşiklerini geçen: **{diagnostics.get('model_screen_passed', 0)}**; henüz nihai değerlendirmeye alınmayan: **{diagnostics.get('not_refined', 0)}**. Nihai rapor sayısı, ligdeki toplam takas sayısı değildir.",
            "",
        ]
    if preliminary:
        lines += [
            "## Ön değerlendirmeyi geçen diğer paketler",
            "",
            "Aşağıdaki puanlar streaming kapalı ön değerlendirmeye aittir. Nihai streaming/hamle planı hesaplanmadığından tamamlanmış takas önerisi değildir.",
            "",
            "| Karşı takım | Verilen | Alınan | Bizim Δ | Karşı taraf Δ |",
            "|---|---|---|---:|---:|",
        ]
        for candidate in preliminary:
            display = candidate.get("display", {})
            gains = candidate["screening"]
            lines.append(
                f"| {display.get('other_team', 'Takım')} | {', '.join(display.get('give', []))} | {', '.join(display.get('receive', []))} | {gains['ours_conservative']:+.3f} | {gains['partner_conservative']:+.3f} |"
            )
        lines.append("")
    evaluated = result.get("evaluated_packages", [])
    if evaluated:
        lines += [
            "## İncelenen bütün paketler",
            "",
            "Ön değerlendirme ile nihai hesap ayrı aşamalardır. Nihai hesap yapılmayan bir satır tamamlanmış takas önerisi değildir.",
            "",
            "| Aşama | Karşı takım | Verilen | Alınan | Bizim Δ | Karşı taraf Δ | Sonuç / neden |",
            "|---|---|---|---|---:|---:|---|",
        ]
        for row in evaluated:
            display, gains = row["display"], row["gains"]
            stage = "Nihai" if row["evaluation_level"] == "final" else "Ön değerlendirme"
            detail = "; ".join(row["reasons"]) or row["status"]
            lines.append(
                f"| {stage} | {display['other_team']} | {', '.join(display['give'])} | {', '.join(display['receive'])} | {gains['ours_conservative']:+.3f} | {gains['partner_conservative']:+.3f} | {detail} |"
            )
        lines.append("")
    for index, candidate in enumerate(result["finalists"], 1):
        display, gains, analysis = candidate["display"], candidate["final"], candidate["analysis"]
        lines += [
            f"## {index}. {display['our_team']} ↔ {display['other_team']}",
            "",
            f"Verilen: **{', '.join(display['give'])}**",
            "",
            f"Alınan: **{', '.join(display['receive'])}**",
            "",
            "Sonuç: **"
            + (
                "Koşullu fırsat"
                if candidate["qualified"]
                else "Model açısından uygun — piyasa incelemesi gerekli"
                if candidate.get("model_qualified")
                else "Tamamlama verisi gerekli"
                if candidate.get("status") == "replacement_data_required"
                else "Öneri dışında"
            )
            + "**",
            "",
            "| Değerlendirme | Bizim Δ | Karşı takımın Δ |",
            "|---|---:|---:|",
            f"| Ön eleme | {candidate['screening']['ours']:+.3f} | {candidate['screening']['partner']:+.3f} |",
            f"| Nihai | {gains['ours']:+.3f} | {gains['partner']:+.3f} |",
            f"| Nihai, iki sakatlık senaryosunun küçüğü | {gains['ours_conservative']:+.3f} | {gains['partner_conservative']:+.3f} |",
            "",
            f"Nihai karar referansı: `{gains['basis']}`.",
            "",
        ]
        capacity = analysis.get("roster_capacity", {})
        if capacity:
            lines += [
                "| Takım | Takas öncesi aktif/bench | Saf takas sonrası | Açık yer önce → sonra |",
                "|---|---:|---:|---:|",
            ]
            for team, row in capacity.items():
                lines.append(
                    f"| {names.get(team, team)} | {row['before_active']} | {row['after_active']} | "
                    f"{row['before_open']} → {row['after_open']} |"
                )
            lines.append("")
        if "improvement_over_original" in candidate:
            lines += [
                f"Mevcut teklife göre temkinli iyileşme: {candidate['improvement_over_original']:+.3f}.",
                "",
            ]
        market = candidate["market"]
        lines += [
            "### Piyasa kontrolü",
            "",
            f"Durum: {market['status']}",
            "",
            f"Kaynak (kullanıcı snapshot'ı): {market['source'] or 'Sağlanmadı'}; "
            f"yakalama zamanı: {market['captured_at'] or 'Yok'}.",
            "",
        ]
        if "totals" in market:
            lines += [
                f"Kaynaklı paket değerleri — verilen: {market['totals']['give']:.3f}; "
                f"alınan: {market['totals']['receive']:.3f}.",
                "",
            ]
        conditions.extend(market["reasons"])
        for signal in market["form_signals"]:
            lines.append(
                f"- {signal['name']}: son {signal['days']} gün sırası {signal['recent_rank']}, "
                f"aynı kaynağın projeksiyon sırası {signal['projected_rank']}. "
                "Bu fark gelecekteki kazancın veya kabulün garantisi değildir."
            )
        lines.append("")
        summaries = _effective_summaries(analysis)
        for team, summary in summaries.items():
            lines += [
                f"### {names.get(team, team)} — kategori değişimi",
                "",
                "| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |",
                "|---|---:|---:|---:|",
            ]
            for category, values in summary["all_supplied_weeks"]["categories"].items():
                lines.append(
                    f"| {category} | %{100 * values['before_win']:.2f} | "
                    f"%{100 * values['after_win']:.2f} | {values['delta_points']:+.3f} |"
                )
            lines.append("")
        stream = analysis.get("streaming", {})
        if stream.get("status") == "planned":
            lines += ["### Nihai streaming hamleleri", ""]
            for path, label in (("before", "Takassız"), ("after", "Takaslı")):
                actions = stream[path]["actions"]
                lines += [f"{label}:", ""]
                if not actions:
                    lines += ["Hamle yok.", ""]
                for action in actions:
                    ending = (
                        f"{analysis['names'][str(action['drop_id'])]} bırakılır."
                        if action["drop_id"] is not None
                        else "mevcut boş kadro yeri kullanılır."
                    )
                    lines.append(
                        f"- {action['date']}: {analysis['names'][str(action['add_id'])]} alınır; {ending}"
                    )
                lines.append("")
        partner = analysis.get("partner_completion", {})
        if partner.get("status") == "applied":
            option = partner["options"][0]
            lines += [
                "### Karşı takımın tamamlayıcı FA hamlesi",
                "",
                f"{names.get(partner['team'], partner['team'])}: {option['date']} günü "
                f"**{option['name']}** alınır; takasla açılan yer kullanılır.",
                "",
                "İki taraf aynı FA'yi kullanmaz; karşılaştırma ortak yönetilmiş kadrolarla yapılır.",
                "",
            ]
        lines.extend(playoff_report_lines(analysis.get("playoff_impact"), names))
        review_reasons = candidate.get("review_reasons", [])
        conditions.extend(review_reasons)
        reasons = candidate.get("blocking_reasons")
        if reasons is None:
            reasons = [r for r in candidate.get("rejection_reasons", []) if r not in review_reasons]
        for reason in dict.fromkeys(reasons):
            lines.append(f"- {reason}")
        conditions.extend(analysis.get("conditions", []))
        lines.append("")
    lines += [
        "## Kapsam ve ölçüm",
        "",
        f"Ön eleme: {result['timings']['screen_seconds']:.3f} sn; "
        f"son değerlendirme: {result['timings']['refine_seconds']:.3f} sn; "
        f"toplam: {result['timings']['total_seconds']:.3f} sn.",
        "",
    ]
    notes = concise_conditions(conditions)
    if notes:
        lines += [
            "",
            "## Veri ve varsayımlar",
            "",
            "Bu ortak koşullar tüm adaylar için bir kez gösterilir. Ham teknik notlar JSON kaydında korunur.",
            "",
        ]
        lines += [f"- {note}" for note in notes]
    if result["errors"]:
        lines += [
            "",
            f"Geçersiz/kısıtlı aday sayısı: {len(result['errors'])}; gerekçeler JSON çıktısında.",
        ]
    return "\n".join(lines) + "\n"
