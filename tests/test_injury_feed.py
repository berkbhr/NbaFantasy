"""Offline ingestion regressions retained from the original parser suite."""

import io
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.nba_injury_scraper import (
    NBAOfficialInjuryScraper,
    candidate_report_urls,
    get_official_report_url,
    parse_report_text,
    reconcilable_team_codes,
)

REAL_FORMAT_REPORT_TEXT = """Injury Report: 01/27/26 12:00 AM
Page 1 of 6
Game Date Game Time Matchup Team Player Name Current Status Reason
01/27/2026 07:00 (ET) POR@WAS Portland Trail Blazers NOT YET SUBMITTED
Washington Wizards Bagley III, Marvin Out Injury/Illness - Thoracic; Strain
Coulibaly, Bilal Questionable Injury/Illness - Lower Back; Strain
Middleton, Khris Questionable Injury/Illness - Left Foot; Soreness
Vukcevic, Tristan Out Injury/Illness - Left Hamstring; Strain
Whitmore, Cam Out
Injury/Illness - Right Shoulder; Deep
Vein Thrombosis
Young, Trae Out
Injury/Illness - Right Knee; MCL
Strain; Quad Contusion
07:30 (ET) SAC@NYK Sacramento Kings LaVine, Zach Questionable Injury/Illness - Lower Back; Soreness
Monk, Malik Questionable Injury/Illness - Right Ankle; Soreness
Murray, Keegan Out Injury/Illness - Left Ankle; Sprain
Plowden, Daeqwon Out G League - Two-Way
Stevens, Isaiah Out G League - Two-Way
New York Knicks Jemison III, Trey Questionable G League - Two-Way
Jones, Dillon Questionable G League - Two-Way
McCullar Jr., Kevin Questionable G League - Two-Way
08:00 (ET) MIL@PHI Milwaukee Bucks Antetokounmpo, Alex Out G League - Two-Way
Antetokounmpo, Giannis Out Injury/Illness - Right Calf; Strain
Porter Jr., Kevin Out
Injury/Illness - Right Oblique Muscle;
Strain
Prince, Taurean Out Injury/Illness - Neck; Surgery
Philadelphia 76ers NOT YET SUBMITTED
10:00 (ET) LAC@UTA LA Clippers Beal, Bradley Out Injury/Illness - Left Hip; Fracture
Dunn, Kris Questionable Injury/Illness - Right Ankle; Sprain
Paul, Chris Out Not With Team
Utah Jazz George, Keyonte Out Rest
Kessler, Walker Out
Injury/Illness - Left Shoulder; Injury
recovery
Markkanen, Lauri Questionable
Return to Competition
Reconditioning
Nurkic, Jusuf Doubtful Injury/Illness - N/A; Illness
"""


class TestScraperParsing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nba_scraper_test_", dir=Path(__file__).resolve().parent)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.scraper = NBAOfficialInjuryScraper(raw_dir=self.tmp)
        self.parsed = parse_report_text(REAL_FORMAT_REPORT_TEXT)
        self.by_raw = {r["raw_name"]: r for r in self.parsed["rows"]}

    @staticmethod
    def _resolver(name):
        return abs(hash(name)) % 100000 + 1

    def test_parses_every_player_row(self):
        self.assertEqual(len(self.parsed["rows"]), 25)
        self.assertEqual(self.parsed["unparsed_lines"], [])

    def test_names_are_flipped_with_suffixes(self):
        for raw, expected in [
            ("Bagley III, Marvin", "Marvin Bagley III"),
            ("Porter Jr., Kevin", "Kevin Porter Jr."),
            ("LaVine, Zach", "Zach LaVine"),
            ("Beal, Bradley", "Bradley Beal"),
            ("Jemison III, Trey", "Trey Jemison III"),
        ]:
            self.assertEqual(self.by_raw[raw]["name"], expected)

    def test_inherited_cells_and_first_row_of_blocks(self):
        # first player of a block is glued to date/time/matchup/team on the same text line
        lav = self.by_raw["LaVine, Zach"]
        self.assertEqual(
            (lav["team"], lav["team_code"], lav["matchup"]), ("Sacramento Kings", "SAC", "SAC@NYK")
        )
        self.assertEqual(self.by_raw["Monk, Malik"]["team"], "Sacramento Kings")
        self.assertEqual(self.by_raw["Monk, Malik"]["game_date"], "01/27/2026")
        self.assertEqual(self.by_raw["Jones, Dillon"]["team"], "New York Knicks")
        self.assertEqual(self.by_raw["Beal, Bradley"]["team"], "LA Clippers")
        self.assertEqual(self.by_raw["Dunn, Kris"]["team"], "LA Clippers")
        self.assertEqual(self.by_raw["Bagley III, Marvin"]["team"], "Washington Wizards")

    def test_wrapped_reasons_and_reason_types(self):
        self.assertTrue(self.by_raw["Whitmore, Cam"]["desc"].endswith("Deep Vein Thrombosis"))
        self.assertEqual(self.by_raw["George, Keyonte"]["reason_type"], "REST")
        self.assertEqual(self.by_raw["Markkanen, Lauri"]["reason_type"], "RETURN_CONDITIONING")
        self.assertEqual(self.by_raw["Plowden, Daeqwon"]["reason_type"], "GLEAGUE")
        self.assertEqual(self.by_raw["Paul, Chris"]["reason_type"], "NOT_WITH_TEAM")
        self.assertEqual(self.by_raw["Beal, Bradley"]["reason_type"], "INJURY")

    def test_unsubmitted_is_tracked_and_never_reconcilable(self):
        unsub = {t["team"] for t in self.parsed["unsubmitted_teams"]}
        self.assertEqual(unsub, {"Portland Trail Blazers", "Philadelphia 76ers"})
        ok, clean, _, _ = self.scraper.run_health_checks(
            self.parsed, games_today_count=3, id_resolver_fn=self._resolver
        )
        recon = reconcilable_team_codes(
            {"clean_injuries": clean, "unsubmitted_teams": self.parsed["unsubmitted_teams"]}
        )
        self.assertNotIn("POR", recon)
        self.assertNotIn("PHI", recon)
        self.assertTrue({"WAS", "SAC", "LAC", "UTA", "MIL"} <= recon)

    def test_g_league_rows_ignored_and_report_healthy(self):
        ok, clean, quarantined, m = self.scraper.run_health_checks(
            self.parsed, games_today_count=3, id_resolver_fn=self._resolver
        )
        self.assertTrue(ok, m["failure_reasons"])
        self.assertEqual(len(clean), 19)
        self.assertEqual(m["ignored_count"], 6)
        self.assertEqual(quarantined, [])

    def test_low_id_resolution_fails_health_check(self):
        ok, *_, m = self.scraper.run_health_checks(
            self.parsed,
            games_today_count=3,
            id_resolver_fn=lambda n: 1 if n.startswith(("K", "M", "C")) else None,
        )
        self.assertFalse(ok)
        self.assertLess(m["match_rate"], 0.85)

    def test_silently_dropped_lines_fail_completeness_check(self):
        bad = parse_report_text(
            REAL_FORMAT_REPORT_TEXT
            + "Mangled, Name Zzz qqq\nAnother, Row Zzz qqq\nThird, Row Zzz qqq\n"
        )
        self.assertEqual(len(bad["unparsed_lines"]), 3)
        ok, _, quarantined, m = self.scraper.run_health_checks(
            bad, games_today_count=3, id_resolver_fn=self._resolver
        )
        self.assertFalse(ok)
        self.assertEqual(m["unparsed_count"], 3)
        self.assertEqual(len(quarantined), 3)

    def test_unknown_status_in_row_list_is_quarantined(self):
        rows = [
            {"name": "Real Player", "status": "OUT", "desc": "Knee"},
            {"name": "Fake Player", "status": "WEIRD_UNKNOWN_STATUS", "desc": "x"},
        ]
        ok, clean, quarantined, _ = self.scraper.run_health_checks(
            rows, games_today_count=1, id_resolver_fn=lambda n: 7
        )
        self.assertEqual(len(clean), 1)
        self.assertEqual(quarantined[0]["row"]["status"], "WEIRD_UNKNOWN_STATUS")

    def test_early_report_with_all_teams_unsubmitted_is_not_a_false_alarm(self):
        early = parse_report_text(
            "Injury Report: 01/28/26 12:00 AM\n"
            "01/28/2026 07:00 (ET) CHI@IND Chicago Bulls NOT YET SUBMITTED\n"
            "Indiana Pacers NOT YET SUBMITTED\n"
        )
        ok, *_ = self.scraper.run_health_checks(early, games_today_count=5)
        self.assertTrue(ok)

    def test_report_time_and_url_naming(self):
        self.assertEqual(self.parsed["report_time_utc"].isoformat(), "2026-01-27T05:00:00+00:00")
        self.assertTrue(
            get_official_report_url(datetime(2026, 1, 27, 5, 0, tzinfo=timezone.utc)).endswith(
                "Injury-Report_2026-01-27_12_00AM.pdf"
            )
        )
        self.assertTrue(
            get_official_report_url(datetime(2026, 1, 27, 22, 7, tzinfo=timezone.utc)).endswith(
                "Injury-Report_2026-01-27_05_00PM.pdf"
            )
        )
        urls = [
            u
            for _, u in candidate_report_urls(datetime(2026, 1, 27, 22, 7, tzinfo=timezone.utc), 3)
        ]
        self.assertTrue(urls[1].endswith("_04_45PM.pdf") and urls[2].endswith("_04_30PM.pdf"))

    def test_fetch_flow_with_fake_downloader(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        writer = PdfWriter()
        page = writer.add_blank_page(width=1000, height=1200)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        lines = ["BT /F1 9 Tf 12 TL 20 1150 Td"]
        for line in REAL_FORMAT_REPORT_TEXT.splitlines():
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            lines.append(f"({escaped}) Tj T*")
        lines.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(lines).encode("latin1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        buf = io.BytesIO()
        writer.write(buf)
        pdf = buf.getvalue()
        calls = []

        def fake(url):
            calls.append(url)
            return pdf if len(calls) == 4 else None  # slots 1-3 are 404

        now = datetime(2026, 1, 27, 22, 7, tzinfo=timezone.utc)
        out = self.scraper.fetch_latest_injuries(
            games_today_count=3,
            id_resolver_fn=self._resolver,
            now=now,
            fetch_bytes_fn=fake,
            pause_seconds=0,
        )
        self.assertTrue(out["is_healthy"], out["metrics"]["failure_reasons"])
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(out["clean_injuries"]), 19)
        self.assertTrue(
            any(f.endswith(".pdf") for f in os.listdir(self.tmp)), "raw PDF was not archived"
        )

        none = self.scraper.fetch_latest_injuries(
            now=now, fetch_bytes_fn=lambda u: None, pause_seconds=0, max_back_steps=3
        )
        self.assertFalse(none["is_healthy"])
