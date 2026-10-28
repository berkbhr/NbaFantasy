"""Read GitHub workflow evidence without exposing credentials or full logs."""

import argparse
import base64
import gzip
import hashlib
import io
import json
import os
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/berkbhr/NbaFantasy"


def session(auth=False):
    client = requests.Session()
    client.headers.update(
        {"Accept": "application/vnd.github+json", "User-Agent": "NBAFantasy-audit"}
    )
    if auth:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            text=True,
            capture_output=True,
            timeout=20,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        if values.get("password"):
            client.headers["Authorization"] = "Bearer " + values["password"]
    return client


def audit(dispatch=False):
    client = session()
    response = client.get(API + "/actions/runs?per_page=8", timeout=30)
    if response.status_code in (401, 403, 404):
        client = session(auth=True)
        response = client.get(API + "/actions/runs?per_page=8", timeout=30)
    response.raise_for_status()
    if dispatch:
        previous = ROOT / "reports/cloud_validation/status.json"
        if previous.exists():
            (previous.parent / "before_dispatch.json").write_bytes(previous.read_bytes())
        client = session(auth=True)
        sent = client.post(
            API + "/actions/workflows/daily_fantasy_sync.yml/dispatches",
            json={"ref": "main"},
            timeout=30,
        )
        sent.raise_for_status()
        print(
            "Workflow dispatch accepted; the configured Telegram notification will be sent.",
            flush=True,
        )
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "runs": []}
    for run in response.json().get("workflow_runs", []):
        item = {
            key: run.get(key)
            for key in ("id", "name", "status", "conclusion", "head_sha", "html_url", "created_at")
        }
        jobs = client.get(API + f"/actions/runs/{run['id']}/jobs", timeout=30)
        if jobs.ok:
            item["jobs"] = [
                {
                    "name": j["name"],
                    "conclusion": j["conclusion"],
                    "steps": [
                        {"name": s["name"], "conclusion": s["conclusion"]}
                        for s in j.get("steps", [])
                    ],
                }
                for j in jobs.json().get("jobs", [])
            ]
        if "Cloud" in str(run.get("name")) and run["status"] == "completed":
            logs = client.get(API + f"/actions/runs/{run['id']}/logs", timeout=30)
            if logs.status_code in (401, 403):
                client = session(auth=True)
                logs = client.get(API + f"/actions/runs/{run['id']}/logs", timeout=30)
            item["logs_http_status"] = logs.status_code
            if logs.ok:
                evidence = []
                with zipfile.ZipFile(io.BytesIO(logs.content)) as archive:
                    for name in archive.namelist():
                        if name.endswith(".txt"):
                            for line in (
                                archive.read(name).decode("utf-8", errors="replace").splitlines()
                            ):
                                if any(
                                    marker in line
                                    for marker in (
                                        "[TELEGRAM]",
                                        "Archived prospective",
                                        "Traceback",
                                        "Error:",
                                        "fatal:",
                                        "RuntimeError:",
                                        "ValueError:",
                                        "to branch nba-fantasy-bot",
                                    )
                                ):
                                    evidence.append(line[-600:])
                item["evidence"] = list(dict.fromkeys(evidence))[-25:]
        report["runs"].append(item)
    tree = client.get(API + "/git/trees/nba-fantasy-bot?recursive=1", timeout=30)
    if tree.ok:
        files = [r["path"] for r in tree.json().get("tree", [])]
        report["runtime_archive"] = {
            "branch_revision": tree.json().get("sha"),
            "predictions": [p for p in files if p.startswith("data/archive/predictions/")],
            "outcome_count": sum(
                p.startswith("data/archive/outcomes/") and p.endswith(".gz") for p in files
            ),
            "injury_report_count": sum(
                p.startswith("data/archive/injury_reports/") and p.endswith(".gz") for p in files
            ),
        }
        report["runtime_archive"]["prediction_blobs"] = {
            r["path"]: r["sha"]
            for r in tree.json().get("tree", [])
            if r["path"].startswith("data/archive/predictions/")
        }
        before_path = ROOT / "reports/cloud_validation/before_dispatch.json"
        if before_path.exists():
            before = (
                json.loads(before_path.read_text(encoding="utf-8"))
                .get("runtime_archive", {})
                .get("prediction_blobs", {})
            )
            if before:
                report["old_prediction_blobs_preserved"] = all(
                    report["runtime_archive"]["prediction_blobs"].get(k) == v
                    for k, v in before.items()
                )
        report["runtime_archive"]["notification_receipt_count"] = sum(
            p.startswith("data/archive/notifications/") and p.endswith(".gz") for p in files
        )

        def contents(path):
            fetched = client.get(API + "/contents/" + path + "?ref=nba-fantasy-bot", timeout=30)
            if not fetched.ok:
                return None
            payload = fetched.json()
            if payload.get("content"):
                return base64.b64decode(payload["content"])
            if payload.get("sha"):
                blob = client.get(API + "/git/blobs/" + payload["sha"], timeout=30)
                if blob.ok and blob.json().get("content"):
                    return base64.b64decode(blob.json()["content"])
            return None

        receipt_raw = contents("reports/delivery_receipt.json")
        if receipt_raw:
            receipt = json.loads(receipt_raw)
            report["latest_receipt"] = receipt
            renderer_digest = hashlib.sha256(
                (ROOT / "src/notifications.py").read_text(encoding="utf-8").encode()
            ).hexdigest()
            report["renderer_version_matches"] = (
                receipt.get("renderer_sha256_LF") == renderer_digest
            )
            prediction_raw = contents(
                "data/archive/predictions/" + receipt["forecast_id"] + ".json.gz"
            )
            if prediction_raw:
                report["receipt_prediction_hash_matches"] = (
                    hashlib.sha256(prediction_raw).hexdigest() == receipt["prediction_sha256"]
                )
                primary = json.loads(gzip.decompress(prediction_raw))["primary"]
                from .notifications import render_telegram
                from .probability import CategoryProbabilities

                probs = CategoryProbabilities(
                    {c: v["win"] for c, v in primary["categories"].items()}
                )
                probs.ties.update({c: v["tie"] for c, v in primary["categories"].items()})
                message = render_telegram(
                    now=datetime.fromisoformat(primary["forecast_at"]),
                    opponent=primary["opponent"],
                    points=primary["objective_value"],
                    probabilities=probs,
                    health=primary["roster_health"],
                    recommendations=primary["recommendations"],
                    live=primary["live_score"],
                    objective=primary["objective"],
                    ownership_audit=primary.get("ownership_audit"),
                    live_score_block_reason=primary.get("live_score_block_reason"),
                )
                report["notification_reproduces_from_archived_forecast"] = (
                    (
                        hashlib.sha256(message.encode()).hexdigest()
                        == receipt["rendered_text_sha256"]
                    )
                    if report["renderer_version_matches"]
                    else None
                )
    path = ROOT / "reports/cloud_validation/status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", action="store_true")
    args = parser.parse_args()
    audit(dispatch=args.dispatch)
