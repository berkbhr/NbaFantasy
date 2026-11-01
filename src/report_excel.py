"""Export existing forecast values as an XLSX workbook, without recalculation."""

import io
import math
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


def forecast_sheets(report):
    """Tables reference the original result; probabilities remain raw fractions."""
    return {
        "Özet": [
            ["NBA Fantasy — yerel rapor", "Değer"],
            ["Rapor zamanı", report.get("forecast_at")],
            ["Görünüm durumu", report.get("display_mode", "Ham rapor")],
            ["Açıklama", report.get("display_message", "")],
            ["Değerlendirme zamanı", report.get("evaluated_at")],
            ["Takım", report.get("my_team")],
            ["Rakip", report.get("opponent")],
            ["Başlangıç", report.get("week_start")],
            ["Bitiş", report.get("week_end")],
            ["Karar hedefi", report.get("objective")],
            ["Hedef değeri", report.get("objective_value")],
            ["Beklenen kategori puanı", report.get("expected_category_points")],
            ["Hafta kazanma olasılığı", report.get("win")],
            ["Hafta beraberlik olasılığı", report.get("draw")],
            ["Hafta kaybetme olasılığı", report.get("loss")],
            ["Olasılık birimi", "0–1 kesir; 0.5 = %50. Yeniden hesaplama yapılmaz."],
        ],
        "Kategoriler": [["Kategori", "Kazanma (0–1)", "Beraberlik (0–1)", "Kaybetme (0–1)"]]
        + [[k, v["win"], v["tie"], v["loss"]] for k, v in report.get("categories", {}).items()],
        "Öngörü": [["İstatistik", "Takım", "Rakip"]]
        + [
            [k, v, report.get("opponent_projected_stats", {}).get(k)]
            for k, v in report.get("my_projected_stats", {}).items()
        ],
        "Hamleler": [["Ekle", "Bırak", "Hedef farkı", "Muhafazakâr fark", "Waiver"]]
        + [
            [
                r.get("add_name"),
                r.get("drop_name"),
                r.get("delta_objective_value"),
                r.get("robust_delta_objective_value"),
                r.get("is_waiver", False),
            ]
            for r in report.get("recommendations", [])
        ],
        "Kadrolar": [["Tarih", "Aktif oyuncu"]]
        + [[day, name] for day, names in report.get("my_lineups", {}).items() for name in names],
        "Veri notları": [["Not"]] + [[str(note)] for note in report.get("notes", [])],
        "Haftalık maçlar": [["Taraf", "Oynanan", "Toplam", "Kalan", "Kaynak zamanı"]]
        + [
            [
                r["side"],
                r.get("played"),
                r.get("total"),
                r.get("remaining"),
                report.get("game_counts_at"),
            ]
            for r in report.get("game_counts", [])
        ],
    }


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
        ]
        links, tabs = [], []
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
                for col, value in enumerate(values, 1):
                    letters, number = "", col
                    while number:
                        number, rest = divmod(number - 1, 26)
                        letters = chr(65 + rest) + letters
                    ref = f"{letters}{row_index}"
                    if (
                        isinstance(value, (float, int))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                    ):
                        cells.append(f'<c r="{ref}"><v>{value!r}</v></c>')
                    else:
                        text = "" if value is None else str(value)
                        text = "".join(c for c in text if c in "\t\n\r" or ord(c) >= 32)
                        cells.append(
                            f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
                        )
                xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
            archive.writestr(
                f"xl/worksheets/sheet{i}.xml",
                f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="40" customWidth="1"/><col min="2" max="8" width="26" customWidth="1"/></cols><sheetData>{"".join(xml_rows)}</sheetData></worksheet>',
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
