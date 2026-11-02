"""Export existing forecast values as an XLSX workbook, without recalculation."""

import io
import math
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

from .report_history import category_results


class ReportRows(list):
    """One reader-facing worksheet, with presentation metadata."""

    def __init__(self):
        super().__init__()
        self.styles = {}
        self.heights = {}
        self.merges = []
        self.hidden_rows = set()
        self.category_range = None

    def row(self, values, style=0, height=24, merge=False):
        self.append(values)
        index = len(self)
        self.heights[index] = height
        for col in range(1, 5):
            self.styles[index, col] = style
        if merge:
            self.merges.append(f"A{index}:D{index}")
        return index


def _excel_time(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return value
        local = stamp.astimezone(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)
        return (local - datetime(1899, 12, 30)).total_seconds() / 86400
    except (ValueError, TypeError, AttributeError):
        return value


def forecast_sheets(report, matches_snapshot=True, history=None):
    """Export the panel view on one sheet. Numeric values are never rounded."""
    rows = ReportRows()
    rows.row([], height=10)
    rows.row(["NBA Fantasy · Haftalık rapor"], 1, 30, merge=True)
    rows.row([f"{report.get('my_team', '')} — {report.get('opponent', '')}"], 1, 28, merge=True)
    rows.row(
        [
            "Hafta",
            f"{report.get('week_start', '')} – {report.get('week_end', '')}",
            "Rapor zamanı (Berlin)",
            _excel_time(report.get("forecast_at")),
        ],
        8,
    )
    rows.styles[4, 4] = 10
    mode = report.get("display_mode", "valid")
    available = report.get("weekly_forecast_available", report.get("live_score_valid", False))
    message = report.get("display_message", "")
    if not matches_snapshot and mode != "last_valid_forecast":
        message = "Güncel kadroyla eşleşme doğrulanmadı. " + message
    rows.row(
        [message] if message else [], 9 if message else 0, 60 if message else 8, merge=bool(message)
    )
    rows.row(
        ["Beklenen kategori puanı", "Hafta kazanma", "Hafta beraberlik", "Hafta kaybetme"], 3, 28
    )
    row = rows.row(
        [
            report.get(k) if available else None
            for k in ("expected_category_points", "win", "draw", "loss")
        ],
        7,
        38,
    )
    rows.styles[row, 1] = 6
    if history:
        rows.row([], height=10)
        rows.row(["Haftalık tahmin takibi"], 2, merge=True)
        rows.row(
            ["Gün başına tek satır: son geçerli tahmin. Hafta başı tahmini ayrıca korunur."],
            8,
            merge=True,
        )
        actual = category_results(history["score"]["board"]) if history.get("score") else None
        actual_points = sum(actual.values()) if actual else None
        opening = history.get("opening")
        index = rows.row(
            [
                "Hafta başı tahmini",
                opening.get("expected_category_points") if opening else "Kayıt yok",
                "Yakalanan sonuç",
                actual_points if actual_points is not None else "Henüz yok",
            ]
        )
        rows.styles[index, 2] = rows.styles[index, 4] = 5
        rows.row(
            ["Gün (Eastern)", "Beklenen kategori puanı", "Hafta kazanma", "Sonuçtan fark (puan)"], 3
        )
        start, end = date.fromisoformat(history["start"]), date.fromisoformat(history["end"])
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            saved = history["days"].get(day.isoformat(), {})
            points = saved.get("expected_category_points")
            index = rows.row(
                [
                    float((day - date(1899, 12, 30)).days),
                    points,
                    saved.get("win"),
                    points - actual_points
                    if points is not None and actual_points is not None
                    else None,
                ]
            )
            rows.styles[index, 1] = 13
            rows.styles[index, 2] = 5
            rows.styles[index, 3] = 4
            rows.styles[index, 4] = 12
        if actual:
            rows.row(
                ["Son skor yakalaması (Berlin)", _excel_time(history["score"]["captured_at"])], 8
            )
            rows.styles[len(rows), 2] = 10
            rows.row(["Kategori", "Hafta başı kazanma", "Son kayıt kazanma", "Yakalanan sonuç"], 3)
            for key, value in actual.items():
                index = rows.row(
                    [
                        {"FG3M": "3PT", "FG_PCT": "FG%", "FT_PCT": "FT%"}.get(key, key),
                        (opening or {}).get("categories", {}).get(key, {}).get("win"),
                        report.get("categories", {}).get(key, {}).get("win"),
                        {1.0: "Galibiyet", 0.5: "Beraberlik", 0.0: "Mağlubiyet"}[value],
                    ]
                )
                rows.styles[index, 2] = rows.styles[index, 3] = 4
            rows.row(
                [
                    "Sonuç, yakalanan Yahoo skorundan hesaplanır. FG/FT için isabet/deneme oranları kullanılır; Yahoo yuvarlaması ve sonraki istatistik düzeltmeleri farklılık yaratabilir."
                ],
                8,
                42,
                merge=True,
            )
        else:
            rows.row(
                [
                    "Hafta sonu skoru henüz yakalanmadı; sonuç karşılaştırması bu kayıt gelince dolar."
                ],
                8,
                merge=True,
            )
    rows.row([], height=10)
    rows.row(["Haftalık maçlar"], 2, merge=True)
    rows.row(["Taraf", "Oynanan", "Toplam", "Kalan"], 3)
    for team in report.get("game_counts", []):
        rows.row(
            [team["side"]]
            + [team.get(k) if team.get("valid") else None for k in ("played", "total", "remaining")]
        )
    if not report.get("game_counts"):
        rows.row(["Maç sayıları doğrulanmadı"], 8, merge=True)
    index = rows.row(
        ["Maç sayılarının kaydı (Berlin)", _excel_time(report.get("game_counts_at"))], 8
    )
    rows.styles[index, 2] = 10
    rows.row([], height=10)
    rows.row(["Kategori görünümü"], 2, merge=True)
    rows.row(["Kategori", "Kazanma", "Beraberlik", "Kaybetme"], 3)
    first = len(rows) + 1
    if available:
        for key, values in report.get("categories", {}).items():
            index = rows.row(
                [
                    {"FG3M": "3PT", "FG_PCT": "FG%", "FT_PCT": "FT%"}.get(key, key),
                    values["win"],
                    values["tie"],
                    values["loss"],
                ],
                4,
                26,
            )
            rows.styles[index, 1] = 0
    if len(rows) >= first:
        rows.category_range = f"B{first}:B{len(rows)}"
    else:
        rows.row(["Geçerli haftalık tahmin yok"], 9, merge=True)
    rows.row([], height=10)
    rows.row(["Hamle seçenekleri"], 2, merge=True)
    rows.row(["Ekle", "Bırak", "Kategori puanı kazancı", "İşlem"], 3)
    moves = report.get("recommendations", []) if available and mode == "valid" else []
    for move in moves:
        index = rows.row(
            [
                move.get("add_name"),
                move.get("drop_name"),
                move.get("delta_objective_value"),
                "Waiver" if move.get("is_waiver") else "Serbest oyuncu",
            ],
            height=28,
        )
        rows.styles[index, 3] = 12
    if not moves:
        message = (
            "Uygun hamle önerisi yok."
            if available and mode == "valid"
            else "Güncel hamleler için yeni geçerli tahmin gerekiyor."
        )
        rows.row([message], 8, merge=True)
    rows.row([], height=10)
    rows.row(["Kadro uyarıları"], 2, merge=True)
    alerts = [
        h for h in report.get("roster_health", []) if h.get("is_out") or h.get("eff_avail", 1) < 0.8
    ]
    if alerts:
        rows.row(["Oyuncu", "Durum", "Kadro yeri", ""], 3)
        for alert in alerts:
            rows.row([alert.get("name"), alert.get("status"), alert.get("slot_state"), ""])
    else:
        rows.row(["Bu raporda kadro uyarısı yok."], 8, merge=True)
    if mode == "last_valid_forecast":
        rows.row(
            [
                "Son geçerli tahminin maç sayıları: "
                + "; ".join(
                    f"{t['side']}: {t.get('played', '?')}/{t.get('total', '?')} oynandı, {t.get('remaining', '?')} kalan"
                    for t in report.get("forecast_game_counts", [])
                )
            ],
            9,
            42,
            merge=True,
        )
    notes = report.get("notes", [])
    if notes:
        rows.row([], height=10)
        rows.row(["Ayrıntılı veri notları (soldaki + ile açılır)"], 2, merge=True)
        for note in notes:
            index = rows.row([str(note)], 11, max(30, 15 * (1 + len(str(note)) // 120)), merge=True)
            rows.hidden_rows.add(index)
    return {"Haftalık rapor": rows}


def workbook_bytes(sheets):
    """Small dependency-free OOXML export; all text is literal, never a formula."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        content = [
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        ]
        links = [f'<Relationship Id="styles" Type="{rel}/styles" Target="styles.xml"/>']
        tabs = []
        archive.writestr("xl/styles.xml", _styles(ns))
        archive.writestr(
            "_rels/.rels",
            f'<Relationships xmlns="{pkg}"><Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        for i, (name, rows) in enumerate(sheets.items(), 1):
            tabs.append(
                f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
            )
            links.append(
                f'<Relationship Id="rId{i}" Type="{rel}/worksheet" Target="worksheets/sheet{i}.xml"/>'
            )
            content.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
            xml_rows = []
            for row_index, values in enumerate(rows, 1):
                cells = []
                if isinstance(rows, ReportRows):
                    values = list(values) + [None] * (4 - len(values))
                for col, value in enumerate(values, 1):
                    letters, number = "", col
                    while number:
                        number, rest = divmod(number - 1, 26)
                        letters = chr(65 + rest) + letters
                    ref = f"{letters}{row_index}"
                    style = getattr(rows, "styles", {}).get((row_index, col), 0)
                    if (
                        isinstance(value, (float, int))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                    ):
                        cells.append(f'<c r="{ref}" s="{style}" t="n"><v>{value!r}</v></c>')
                    else:
                        text = "" if value is None else str(value)
                        text = "".join(c for c in text if c in "\t\n\r" or ord(c) >= 32)
                        cells.append(
                            f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
                        )
                height = getattr(rows, "heights", {}).get(row_index, 24)
                hidden = (
                    ' hidden="1" outlineLevel="1"'
                    if row_index in getattr(rows, "hidden_rows", set())
                    else ""
                )
                xml_rows.append(
                    f'<row r="{row_index}" ht="{height}" customHeight="1"{hidden}>{"".join(cells)}</row>'
                )
            merges = getattr(rows, "merges", [])
            merge_xml = (
                '<mergeCells count="'
                + str(len(merges))
                + '">'
                + "".join(f'<mergeCell ref="{r}"/>' for r in merges)
                + "</mergeCells>"
                if merges
                else ""
            )
            category = getattr(rows, "category_range", None)
            bars = (
                f'<conditionalFormatting sqref="{category}"><cfRule type="dataBar" priority="1"><dataBar><cfvo type="num" val="0"/><cfvo type="num" val="1"/><color rgb="FFBCD982"/></dataBar></cfRule></conditionalFormatting>'
                if category
                else ""
            )
            archive.writestr(
                f"xl/worksheets/sheet{i}.xml",
                f'<worksheet xmlns="{ns}"><sheetPr><outlinePr summaryBelow="0"/><pageSetUpPr fitToPage="1"/></sheetPr><sheetViews><sheetView workbookViewId="0" showGridLines="0" zoomScale="90"/></sheetViews><cols><col min="1" max="1" width="34" customWidth="1"/><col min="2" max="2" width="30" customWidth="1"/><col min="3" max="4" width="27" customWidth="1"/></cols><sheetData>{"".join(xml_rows)}</sheetData>{merge_xml}{bars}<pageMargins left="0.25" right="0.25" top="0.35" bottom="0.35" header="0.1" footer="0.1"/><pageSetup paperSize="9" orientation="portrait" fitToWidth="1" fitToHeight="0"/></worksheet>',
            )
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets>{"".join(tabs)}</sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<Relationships xmlns="{pkg}">{"".join(links)}</Relationships>',
        )
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            + "".join(content)
            + "</Types>",
        )
    return stream.getvalue()


def _styles(ns):
    fonts = "".join(
        f'<font><sz val="{size}"/><color rgb="FF{color}"/><name val="Arial"/>{"<b/>" if bold else ""}</font>'
        for size, color, bold in [
            (11, "25313A", False),
            (16, "172128", True),
            (11, "FFFFFF", True),
            (11, "25313A", True),
            (18, "203312", True),
            (10, "596570", False),
            (11, "805A10", False),
        ]
    )
    fills = (
        '<fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
        + "".join(
            f'<fill><patternFill patternType="solid"><fgColor rgb="FF{color}"/><bgColor indexed="64"/></patternFill></fill>'
            for color in ["20292F", "E8EDF0", "F0F6E6", "FFF3D6"]
        )
    )
    # font, fill, number format, alignment, wrap
    definitions = [
        (0, 0, 0, "left", 0),
        (1, 0, 0, "left", 0),
        (2, 2, 0, "left", 0),
        (3, 3, 0, "center", 1),
        (0, 0, 164, "right", 0),
        (0, 0, 2, "right", 0),
        (4, 4, 166, "center", 0),
        (4, 4, 164, "center", 0),
        (5, 0, 0, "left", 0),
        (6, 5, 0, "left", 1),
        (5, 0, 165, "right", 0),
        (5, 0, 0, "left", 1),
        (0, 0, 167, "right", 0),
        (0, 0, 168, "left", 0),
    ]
    xfs = "".join(
        f'<xf fontId="{font}" fillId="{fill}" numFmtId="{fmt}" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="{align}" vertical="center" wrapText="{wrap}"/></xf>'
        for font, fill, fmt, align, wrap in definitions
    )
    return f'<styleSheet xmlns="{ns}"><numFmts count="5"><numFmt numFmtId="164" formatCode="0.0%"/><numFmt numFmtId="165" formatCode="dd.mm.yyyy hh:mm"/><numFmt numFmtId="166" formatCode="0.00&quot; / 9&quot;"/><numFmt numFmtId="167" formatCode="+0.00;-0.00;0.00"/><numFmt numFmtId="168" formatCode="dd.mm.yyyy"/></numFmts><fonts count="7">{fonts}</fonts><fills count="6">{fills}</fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="14">{xfs}</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
