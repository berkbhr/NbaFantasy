"""
NBA official injury report ingestion (v2).

Real report layout (observed on an official PDF, 27 Jan 2026):

    Game Date Game Time Matchup Team Player Name Current Status Reason
    01/27/2026 07:00 (ET) POR@WAS Portland Trail Blazers NOT YET SUBMITTED
    Washington Wizards Bagley III, Marvin Out Injury/Illness - Thoracic; Strain
    Coulibaly, Bilal Questionable Injury/Illness - Lower Back; Strain
    Whitmore, Cam Out
    Injury/Illness - Right Shoulder; Deep
    Vein Thrombosis
    07:30 (ET) SAC@NYK Sacramento Kings LaVine, Zach Questionable Injury/Illness - ...

Key facts handled here:
  * It is a PDF (not HTML). Text must be extracted before parsing.
  * Date / time / matchup / team cells are inherited by the rows below them and can be
    glued to the FIRST player of a block on the same text line.
  * Names are "Last, First" with suffixes on the last name ("Porter Jr., Kevin").
  * Reasons can wrap onto the following lines.
  * Teams that have not reported appear as "NOT YET SUBMITTED". That is NOT "healthy".
  * Rows such as "G League - Two-Way" are not injuries and are ignored by default.
  * File names look like Injury-Report_2026-01-27_12_00AM.pdf (ET clock, 15-minute steps).

IMPORTANT: validate the PDF text extraction once against a REAL downloaded PDF and save it
as a test fixture (see tests). The parser is written for the line layout shown above; the
extraction library may order words differently on some pages. The completeness check in
run_health_checks() exists to make such a failure loud instead of silent.
"""
import io
import os
import re
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger("InjuryScraper")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
RAW_INJURY_DIR = os.path.join(DATA_DIR, 'raw', 'injuries')

REPORT_URL_TEMPLATE = "https://ak-static.cms.nba.com/referee/injury/{name}"

# Statuses that can come out of the official report, plus legacy/manual/Yahoo ones that
# the tracker also understands.
REPORT_STATUSES = ('OUT', 'QUESTIONABLE', 'DOUBTFUL', 'PROBABLE', 'AVAILABLE')
VALID_STATUSES = set(REPORT_STATUSES) | {'GTD', 'DTD', 'INJ', 'SUSPENDED', 'REST'}

# Rows with these reason types are not injury information for fantasy purposes.
DEFAULT_IGNORED_REASON_TYPES = ('GLEAGUE',)

TEAM_NAME_TO_CODE = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}
# Alternate spellings that may appear in some extractions.
TEAM_ALIASES = {
    "Los Angeles Clippers": "LA Clippers",
    "LA Lakers": "Los Angeles Lakers",
    "Philadelphia Sixers": "Philadelphia 76ers",
}
# Longest first so that prefix matching is unambiguous.
_ALL_TEAM_NAMES = sorted(list(TEAM_NAME_TO_CODE) + list(TEAM_ALIASES), key=len, reverse=True)

_ET_TZ = None


def _eastern_tz():
    """US Eastern time zone. Falls back to a fixed UTC-5 offset if tzdata is unavailable."""
    global _ET_TZ
    if _ET_TZ is None:
        try:
            from zoneinfo import ZoneInfo
            _ET_TZ = ZoneInfo("America/New_York")
        except Exception:
            logger.warning("zoneinfo/tzdata unavailable (pip install tzdata). "
                           "Using fixed UTC-5; report URLs may be off by one hour during DST.")
            _ET_TZ = timezone(timedelta(hours=-5))
    return _ET_TZ


def to_eastern(dt):
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_eastern_tz())


def flip_last_first(name_str):
    """'Porter Jr., Kevin' -> 'Kevin Porter Jr.'. Names already in 'First Last' order are kept."""
    if not name_str:
        return ''
    s = str(name_str).strip()
    if ',' in s:
        last, first = [p.strip() for p in s.split(',', 1)]
        return f"{first} {last}".strip()
    return s


def report_file_name(dt_et):
    """Injury-Report_2026-01-27_12_00AM.pdf  (12-hour ET clock, 'HH_MM' then AM/PM)."""
    hour12 = dt_et.hour % 12 or 12
    ampm = 'AM' if dt_et.hour < 12 else 'PM'
    return f"Injury-Report_{dt_et:%Y-%m-%d}_{hour12:02d}_{dt_et.minute:02d}{ampm}.pdf"


def get_official_report_url(dt=None):
    """URL of the report published at the given ET moment (rounded down to 15 minutes)."""
    dt_et = to_eastern(dt)
    dt_et = dt_et.replace(minute=(dt_et.minute // 15) * 15, second=0, microsecond=0)
    return REPORT_URL_TEMPLATE.format(name=report_file_name(dt_et))


def candidate_report_urls(now=None, max_back_steps=32):
    """Newest-first list of possible report URLs at 15-minute steps (default: last 8 hours)."""
    dt_et = to_eastern(now)
    dt_et = dt_et.replace(minute=(dt_et.minute // 15) * 15, second=0, microsecond=0)
    urls = []
    for i in range(max_back_steps):
        t = dt_et - timedelta(minutes=15 * i)
        urls.append((t, REPORT_URL_TEMPLATE.format(name=report_file_name(t))))
    return urls


def extract_text_from_pdf(pdf_bytes):
    """Extract text with pdfplumber (preferred) or pypdf. Raises a clear error if neither exists."""
    errors = []
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or '')
        return "\n".join(pages)
    except ImportError:
        errors.append("pdfplumber not installed")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join((p.extract_text() or '') for p in reader.pages)
    except ImportError:
        errors.append("pypdf not installed")
    raise RuntimeError("No PDF text extractor available (" + "; ".join(errors) +
                       "). Install one: pip install pdfplumber")


# ----------------------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------------------
_RE_DATE = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+')
_RE_TIME = re.compile(r'^(\d{1,2}:\d{2})\s*\(ET\)\s+', re.IGNORECASE)
_RE_MATCHUP = re.compile(r'^([A-Z]{2,3}@[A-Z]{2,3})\s+')
_RE_HEADER_TS = re.compile(r'Injury Report:\s*(\d{2}/\d{2}/\d{2,4})\s+(\d{1,2}:\d{2}\s*[AP]M)', re.IGNORECASE)
_RE_PAGE = re.compile(r'^Page\s+\d+\s+of\s+\d+$', re.IGNORECASE)

_NAME_WORD = r"[^\W\d_][\w\.\'\u2019\-]*"            # letter-initial word, unicode aware
_RE_PLAYER_ROW = re.compile(
    r"^(?P<last>" + _NAME_WORD + r"(?: " + _NAME_WORD + r"){0,3}),\s+"
    r"(?P<first>" + _NAME_WORD + r")\s+"
    r"(?P<status>(?i:Out|Questionable|Doubtful|Probable|Available))\b\s*(?P<reason>.*)$"
)
# A line that LOOKS like "Last, First ..." but did not match a full row (for completeness checks)
_RE_NAME_LIKE = re.compile(r"^" + _NAME_WORD + r"(?: " + _NAME_WORD + r"){0,3},\s+" + _NAME_WORD + r"\b")


def classify_reason(desc):
    d = (desc or '').strip().lower()
    if not d:
        return 'NONE'
    if d.startswith('injury/illness'):
        return 'INJURY'
    if d.startswith('g league'):
        return 'GLEAGUE'
    if d.startswith('rest'):
        return 'REST'
    if d.startswith('not with team'):
        return 'NOT_WITH_TEAM'
    if d.startswith('personal'):
        return 'PERSONAL'
    if d.startswith('suspension'):
        return 'SUSPENSION'
    if d.startswith('return to competition'):
        return 'RETURN_CONDITIONING'
    if d.startswith('trade'):
        return 'TRADE'
    return 'OTHER'


def _strip_prefix(line, state):
    """Peel date / time / matchup / team cells off the start of a line, updating inherited state."""
    changed = True
    while changed:
        changed = False
        m = _RE_DATE.match(line)
        if m:
            state['date'] = m.group(1)
            line = line[m.end():]
            changed = True
            continue
        m = _RE_TIME.match(line)
        if m:
            state['time'] = m.group(1)
            line = line[m.end():]
            changed = True
            continue
        m = _RE_MATCHUP.match(line)
        if m:
            state['matchup'] = m.group(1)
            line = line[m.end():]
            changed = True
            continue
        for name in _ALL_TEAM_NAMES:
            if line == name or line.startswith(name + ' '):
                state['team'] = TEAM_ALIASES.get(name, name)
                line = line[len(name):].lstrip()
                changed = True
                break
    return line


def parse_report_time(text):
    """Report timestamp from the page header, e.g. 'Injury Report: 01/27/26 12:00 AM' (ET) -> aware UTC datetime."""
    m = _RE_HEADER_TS.search(text or '')
    if not m:
        return None
    d, t = m.group(1), re.sub(r'\s+', ' ', m.group(2).upper())
    for fmt in ("%m/%d/%y %I:%M %p", "%m/%d/%Y %I:%M %p"):
        try:
            naive = datetime.strptime(f"{d} {t}", fmt)
            return naive.replace(tzinfo=_eastern_tz()).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def parse_report_text(text):
    """
    Parse extracted report text.

    Returns dict with:
      rows               list of player rows (all reason types, incl. G League)
      unsubmitted_teams  [{'team','team_code','matchup','game_date'}]  (unverified, NOT healthy)
      unparsed_lines     lines that look like player rows but could not be parsed
      candidate_count    rows + unparsed_lines (for the completeness check)
      report_time_utc    datetime or None
    """
    rows, unsubmitted, unparsed = [], [], []
    state = {'date': None, 'time': None, 'matchup': None, 'team': None}
    last_row = None

    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith('injury report:') or _RE_PAGE.match(line):
            continue
        if line.lower().startswith('game date') and 'player name' in line.lower():
            continue

        remainder = _strip_prefix(line, state)
        if not remainder:
            continue

        if 'NOT YET SUBMITTED' in remainder.upper():
            unsubmitted.append({
                'team': state['team'] or 'UNKNOWN',
                'team_code': TEAM_NAME_TO_CODE.get(state['team']),
                'matchup': state['matchup'],
                'game_date': state['date'],
            })
            last_row = None
            continue

        m = _RE_PLAYER_ROW.match(remainder)
        if m:
            raw_name = f"{m.group('last')}, {m.group('first')}"
            last_row = {
                'game_date': state['date'],
                'game_time': state['time'],
                'matchup': state['matchup'],
                'team': state['team'],
                'team_code': TEAM_NAME_TO_CODE.get(state['team']),
                'raw_name': raw_name,
                'name': flip_last_first(raw_name),
                'status': m.group('status').upper(),
                'desc': m.group('reason').strip(),
                'source': 'nba_official_scraper',
            }
            rows.append(last_row)
            continue

        if _RE_NAME_LIKE.match(remainder):
            unparsed.append(raw_line.strip())
            last_row = None
            continue

        # Wrapped reason text belongs to the previous player row.
        if last_row is not None:
            last_row['desc'] = (last_row['desc'] + ' ' + remainder).strip()

    for r in rows:
        r['reason_type'] = classify_reason(r['desc'])

    return {
        'rows': rows,
        'unsubmitted_teams': unsubmitted,
        'unparsed_lines': unparsed,
        'candidate_count': len(rows) + len(unparsed),
        'report_time_utc': parse_report_time(text),
    }


def reconcilable_team_codes(result):
    """
    Teams whose absence of a player may be read as 'no longer listed'.
    Only teams that appear in the report with at least one row AND are not 'NOT YET SUBMITTED'.
    A team that is absent from the report entirely is UNKNOWN, not healthy.
    Pass the result as clear_unlisted_teams to InjuryTracker.bulk_sync_yahoo_statuses.
    """
    unsub = {t['team_code'] for t in result.get('unsubmitted_teams', []) if t.get('team_code')}
    seen = {r['team_code'] for r in result.get('clean_injuries', []) if r.get('team_code')}
    return seen - unsub


# ----------------------------------------------------------------------------------------
# Source
# ----------------------------------------------------------------------------------------
class InjurySource(ABC):
    """Abstract Base Class for Injury Ingestion Sources."""
    @abstractmethod
    def fetch_latest_injuries(self, games_today_count=None):
        pass


def _default_fetch_bytes(url, timeout=12.0):
    """Returns bytes, or None when the file does not exist (404/403) or the network fails."""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except HTTPError as e:
        if e.code not in (403, 404):
            logger.warning(f"HTTP {e.code} for {url}")
        return None
    except (URLError, OSError) as e:
        logger.warning(f"Network error for {url}: {e}")
        return None


class NBAOfficialInjuryScraper(InjurySource):
    """
    Official NBA injury report ingestion:
      1. Finds the newest published PDF by probing 15-minute ET steps backwards.
      2. Archives the raw PDF before parsing (re-parse later if the layout changes).
      3. Extracts text (pdfplumber/pypdf) and parses the real layout incl. inherited cells.
      4. 'NOT YET SUBMITTED' teams are tracked as unverified, never as healthy.
      5. Row-level quarantine + a completeness check that catches silently dropped rows.
      6. Never writes to the DB itself; the caller decides based on is_healthy.
    """
    def __init__(self, raw_dir=RAW_INJURY_DIR, stale_hours_threshold=18.0,
                 ignored_reason_types=DEFAULT_IGNORED_REASON_TYPES, max_unparsed_ratio=0.05):
        self.raw_dir = raw_dir
        self.stale_hours_threshold = stale_hours_threshold
        self.ignored_reason_types = set(ignored_reason_types or ())
        self.max_unparsed_ratio = max_unparsed_ratio
        try:
            os.makedirs(self.raw_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create raw archive dir {self.raw_dir}: {e}")

    # -- archive -----------------------------------------------------------------------
    def archive_raw_payload(self, raw_bytes, extension="pdf", label=""):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        tag = f"_{label}" if label else ""
        filepath = os.path.join(self.raw_dir, f"injury_report_{ts}{tag}.{extension}")
        try:
            with open(filepath, 'wb') as f:
                f.write(raw_bytes)
            logger.info(f"Archived raw injury payload to {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"Could not archive raw payload ({e})")
            return None

    # -- staleness ---------------------------------------------------------------------
    def check_snapshot_staleness(self, last_updated_iso, games_today_count=None):
        """
        Warns if the snapshot is older than the threshold. Pass the REPORT time
        (result['report_time_utc'].isoformat()), not the fetch time.
        On days with 0 scheduled games the threshold is 48 hours to avoid false alarms.
        """
        if not last_updated_iso:
            return True, "No snapshot timestamp recorded"
        try:
            dt = datetime.fromisoformat(str(last_updated_iso).replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
            eff_threshold = 48.0 if (games_today_count == 0) else self.stale_hours_threshold
            is_stale = age_hours > eff_threshold
            msg = f"Snapshot age: {age_hours:.1f} hrs (Threshold: {eff_threshold} hrs)"
            if is_stale:
                logger.warning(f"STALE INJURY DATA ALERT: {msg}")
            return is_stale, msg
        except Exception as e:
            return True, f"Invalid timestamp format: {e}"

    # -- health checks -----------------------------------------------------------------
    def run_health_checks(self, parsed_payload, games_today_count=None, id_resolver_fn=None):
        """
        Returns (is_healthy, clean_rows, quarantined_rows, metrics).
        Accepts the dict from parse_report_text() or a plain list of rows (legacy/tests).
        """
        if isinstance(parsed_payload, dict):
            parsed_rows = parsed_payload.get('rows', [])
            unsubmitted = parsed_payload.get('unsubmitted_teams', [])
            unparsed_lines = parsed_payload.get('unparsed_lines', [])
        else:
            parsed_rows, unsubmitted, unparsed_lines = list(parsed_payload), [], []

        clean_rows, quarantined, ignored = [], [], []
        resolved_count = 0

        for row in parsed_rows:
            player_name = (row.get('name') or '').strip()
            raw_status = (row.get('status') or '').upper().strip()

            if not player_name or raw_status not in VALID_STATUSES:
                quarantined.append({
                    'row': row,
                    'reason': f"Unknown status: '{raw_status}'" if player_name else "Empty player name",
                })
                continue
            if row.get('reason_type') in self.ignored_reason_types:
                ignored.append(row)
                continue

            pid = id_resolver_fn(player_name) if id_resolver_fn else None
            if pid is not None:
                resolved_count += 1
                row['player_id'] = pid
            clean_rows.append(row)

        for line in unparsed_lines:
            quarantined.append({'row': {'raw_line': line}, 'reason': 'Unparsed player-like line'})

        total_valid = len(clean_rows)
        match_rate = (resolved_count / total_valid) if total_valid > 0 else 1.0

        # Expected volume scales with how many teams actually reported.
        teams_listed = {r.get('team') for r in parsed_rows if r.get('team')} | \
                       {t.get('team') for t in unsubmitted if t.get('team')}
        unsub_ratio = (len({t.get('team') for t in unsubmitted}) / len(teams_listed)) if teams_listed else 0.0
        if games_today_count is None:
            min_expected = 0 if unsub_ratio >= 1.0 else 2
        elif games_today_count == 0:
            min_expected = 0
        else:
            min_expected = int(max(1, games_today_count) * (1.0 - unsub_ratio))

        candidates = len(parsed_rows) + len(unparsed_lines)
        unparsed_ratio = (len(unparsed_lines) / candidates) if candidates else 0.0

        metrics = {
            'total_parsed': len(parsed_rows),
            'clean_count': total_valid,
            'ignored_count': len(ignored),
            'quarantined_count': len(quarantined),
            'unparsed_count': len(unparsed_lines),
            'unparsed_ratio': unparsed_ratio,
            'resolved_id_count': resolved_count,
            'match_rate': match_rate,
            'min_expected': min_expected,
            'unsubmitted_teams_count': len(unsubmitted),
            'unsubmitted_teams': unsubmitted,
        }

        failure_reasons = []
        if total_valid < min_expected:
            failure_reasons.append(f"Clean rows ({total_valid}) below dynamic expectation ({min_expected})")
        if total_valid >= 5 and match_rate < 0.85:
            failure_reasons.append(f"Player ID resolution rate ({match_rate * 100:.1f}%) below 85% threshold")
        if len(unparsed_lines) > 0 and unparsed_ratio > self.max_unparsed_ratio:
            failure_reasons.append(
                f"Parser could not read {len(unparsed_lines)} of {candidates} player-like lines "
                f"({unparsed_ratio * 100:.1f}% > {self.max_unparsed_ratio * 100:.0f}%)")

        is_healthy = not failure_reasons
        metrics['is_healthy'] = is_healthy
        metrics['failure_reasons'] = failure_reasons
        metrics['ignored_rows'] = ignored

        if not is_healthy:
            logger.error(f"Health check FAILED: {failure_reasons}. Quarantined {len(quarantined)} rows.")
        else:
            logger.info(f"Health check PASSED ({total_valid} rows clean, {len(ignored)} ignored, "
                        f"{len(quarantined)} quarantined, {len(unsubmitted)} unsubmitted).")
        return is_healthy, clean_rows, quarantined, metrics

    # -- parsing entry point -----------------------------------------------------------
    def _parse_payload(self, payload):
        """PDF bytes -> text -> rows. Plain str / non-PDF bytes are parsed as text."""
        if not payload:
            return {'rows': [], 'unsubmitted_teams': [], 'unparsed_lines': [],
                    'candidate_count': 0, 'report_time_utc': None}
        if isinstance(payload, (bytes, bytearray)):
            if bytes(payload[:5]) == b'%PDF-':
                text = extract_text_from_pdf(bytes(payload))
            else:
                text = bytes(payload).decode('utf-8', errors='ignore')
        else:
            text = str(payload)
        return parse_report_text(text)

    # -- fetch -------------------------------------------------------------------------
    def fetch_latest_injuries(self, games_today_count=None, id_resolver_fn=None, now=None,
                              max_back_steps=32, fetch_bytes_fn=None, pause_seconds=0.2):
        """
        Probe 15-minute report slots newest-first until a PDF is found, archive it, parse it,
        run health checks. Never raises on network/parse problems; returns is_healthy=False.
        """
        fetch_bytes_fn = fetch_bytes_fn or _default_fetch_bytes
        raw_bytes, source_url, source_slot = None, None, None

        for slot, url in candidate_report_urls(now, max_back_steps):
            data = fetch_bytes_fn(url)
            if data:
                raw_bytes, source_url, source_slot = data, url, slot
                break
            if pause_seconds:
                time.sleep(pause_seconds)

        empty = {'rows': [], 'unsubmitted_teams': [], 'unparsed_lines': [],
                 'candidate_count': 0, 'report_time_utc': None}
        parse_error = None
        parsed = empty
        if raw_bytes is None:
            logger.warning(f"No report PDF found in the last {max_back_steps} 15-minute slots.")
        else:
            self.archive_raw_payload(raw_bytes, extension="pdf",
                                     label=os.path.splitext(os.path.basename(source_url))[0])
            try:
                parsed = self._parse_payload(raw_bytes)
            except Exception as e:                      # extraction library missing/broken, bad PDF...
                parse_error = str(e)
                logger.error(f"Report parsing failed: {e}")

        is_healthy, clean_rows, quarantined, metrics = self.run_health_checks(
            parsed, games_today_count=games_today_count, id_resolver_fn=id_resolver_fn)

        if raw_bytes is None:
            is_healthy = False
            metrics['failure_reasons'] = metrics['failure_reasons'] + ["No report PDF found"]
        if parse_error:
            is_healthy = False
            metrics['failure_reasons'] = metrics['failure_reasons'] + [f"Parse error: {parse_error}"]
        metrics['is_healthy'] = is_healthy

        result = {
            'is_healthy': is_healthy,
            'clean_injuries': clean_rows,
            'quarantined': quarantined,
            'ignored': metrics.get('ignored_rows', []),
            'unsubmitted_teams': parsed.get('unsubmitted_teams', []),
            'metrics': metrics,
            'source_url': source_url,
            'report_time_utc': parsed.get('report_time_utc'),
            'fetched_at': datetime.now(timezone.utc).isoformat(),
        }
        result['reconcilable_team_codes'] = reconcilable_team_codes(result)
        return result
