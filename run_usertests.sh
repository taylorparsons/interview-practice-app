#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  PYTHON_BIN="python"
elif [[ -x "${ROOT_DIR}/venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "python executable not found on PATH. Activate the project's virtualenv or install Python 3.11+." >&2
  exit 1
fi

REQ_FILE="${ROOT_DIR}/requirements-dev.txt"
if [[ ! -f "${REQ_FILE}" ]]; then
  echo "Missing ${REQ_FILE}. Cannot install UI testing dependencies." >&2
  exit 1
fi

echo "[run_usertests] Installing Helium UI testing dependencies using ${PYTHON_BIN}..."
"${PYTHON_BIN}" -m pip install --requirement "${REQ_FILE}"

export UI_BASE_URL="${UI_BASE_URL:-http://localhost:8000}"
echo "[run_usertests] Running Helium UI tests against ${UI_BASE_URL}"

if command -v curl >/dev/null 2>&1; then
  if ! curl --silent --fail --max-time 3 "${UI_BASE_URL}" >/dev/null; then
    echo "[run_usertests] Could not reach ${UI_BASE_URL}. Start the FastAPI server first or set UI_BASE_URL." >&2
    exit 1
  fi
else
  "${PYTHON_BIN}" - <<'PY' "${UI_BASE_URL}"
import sys
import urllib.request

url = sys.argv[1]
try:
    urllib.request.urlopen(url, timeout=3)
except Exception:
    print(f"[run_usertests] Could not reach {url}. Start the FastAPI server first or set UI_BASE_URL.", file=sys.stderr)
    sys.exit(1)
PY
fi

cd "${ROOT_DIR}"
REPORT_DIR="${ROOT_DIR}/tests/ui/__artifacts__"
mkdir -p "${REPORT_DIR}"
PYTEST_LOG="${REPORT_DIR}/usertests.pytest.log"
JUNIT_XML="${REPORT_DIR}/usertests.junit.xml"
SUMMARY_MD="${REPORT_DIR}/usertests_report.md"

set +e
"${PYTHON_BIN}" -m pytest tests/ui --maxfail=1 --disable-warnings --tb=short --junitxml "${JUNIT_XML}" "$@" 2>&1 | tee "${PYTEST_LOG}"
PYTEST_STATUS=${PIPESTATUS[0]}
set -e

"${PYTHON_BIN}" - <<'PY' "${JUNIT_XML}" "${SUMMARY_MD}" "${PYTEST_STATUS}"
import sys
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import re

xml_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
exit_code = int(sys.argv[3])
artifacts_root = report_path.parent

TEST_META = {
    "tests.ui.test_homepage_smoke::test_homepage_upload_section_visible": {
        "journey": "Candidate landing experience",
        "proves": "Resume and job description upload controls render, so a candidate can begin the practice flow.",
        "why": "If this UI regresses, users cannot start the interview journey and churn immediately.",
        "cta": "Investigate recent UI/layout changes and restore the upload form parity."
    },
    "tests.ui.test_coach_persona_default::test_default_discovery_coach_selected": {
        "journey": "Coach persona defaults",
        "proves": "Discovery persona is preselected and the onboarding upload flow transitions into the interview view.",
        "why": "Wrong defaults or a broken transition will confuse candidates and stall their preparation.",
        "cta": "Restore the default persona wiring or adjust fixtures if the UX intentionally changed."
    },
    "tests.ui.test_voice_session_flow::test_voice_session_happy_path": {
        "journey": "Realtime voice kickoff",
        "proves": "Starting a voice session updates status indicators and streams agent guidance into the transcript panel.",
        "why": "If voice bootstrap breaks, candidates lose the signature realtime coaching experience.",
        "cta": "Inspect recent WebRTC or fetch changes and ensure the coach can reach 'Live' status."
    },
    "tests.ui.test_voice_session_flow::test_voice_session_remember_and_persona": {
        "journey": "Voice transcript persistence",
        "proves": "Remembering a transcript snippet and switching personas update both storage and UI feedback.",
        "why": "If memorize calls or persona persistence fail, voice practice no longer reinforces user prompts.",
        "cta": "Verify storage endpoints and localStorage writes still complete under voice interaction."
    },
    "tests.ui.test_voice_session_flow::test_voice_session_error_recovery": {
        "journey": "Voice failure handling",
        "proves": "Session creation errors surface to the user and controls remain usable for retries.",
        "why": "Silent failures trap candidates without feedback and block retries during outages.",
        "cta": "Confirm error messaging and button states respond to upstream failures."
    },
    "tests.ui.test_voice_session_flow::test_voice_session_manual_stop": {
        "journey": "Voice teardown",
        "proves": "Manual stop closes realtime channels, resets controls, and readies the UI for another session.",
        "why": "Lingering connections or stale controls would drain resources and confuse candidates looping sessions.",
        "cta": "Ensure teardown logic restores default state and closes peer/data channels."
    },
}

DEFAULT_META = {
    "journey": "Undocumented scenario",
    "proves": "Add this test to TEST_META in run_usertests.sh for richer reporting.",
    "why": "Future teammates should understand the customer impact of this check.",
    "cta": "Document intent and coverage so stakeholders know why it matters."
}

def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")

def _latest_flow_artifact(test_id: str) -> str:
    slug = _slugify(test_id.split("::")[-1])
    candidates = sorted(
        (p for p in artifacts_root.glob(f"{slug}_*") if p.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return str(candidates[0]) if candidates else "—"

def load_cases():
    if not xml_path.exists():
        return []
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suites = []
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        suites = [root]
    cases = []
    for suite in suites:
        for case in suite.findall("testcase"):
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            key = f"{classname}::{name}" if classname else name
            meta = TEST_META.get(key, DEFAULT_META)
            result = "PASSED"
            detail = "Scenario validated."
            if case.find("failure") is not None:
                failure = case.find("failure")
                result = "FAILED"
                detail = (failure.attrib.get("message") or failure.text or "").strip()
            elif case.find("error") is not None:
                error = case.find("error")
                result = "ERROR"
                detail = (error.attrib.get("message") or error.text or "").strip()
            elif case.find("skipped") is not None:
                skipped = case.find("skipped")
                result = "SKIPPED"
                detail = (skipped.attrib.get("message") or skipped.text or "").strip()
            cases.append(
                {
                    "id": key,
                    "name": name,
                    "result": result,
                    "detail": detail or "No additional details.",
                    "artifacts": _latest_flow_artifact(key),
                    **meta,
                }
            )
    return cases

cases = load_cases()
total = len(cases)
passed = sum(1 for c in cases if c["result"] == "PASSED")
failed = sum(1 for c in cases if c["result"] in {"FAILED", "ERROR"})
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
overall_status = "PASSED" if exit_code == 0 else "FAILED"

lines = []
lines.append("# Helium User Test Report")
lines.append("")
lines.append(f"- **Generated:** {timestamp}")
lines.append(f"- **Status:** {overall_status} ({passed}/{total} passing)")
lines.append(f"- **Log:** `{report_path.parent / 'usertests.pytest.log'}`")
lines.append("")

if cases:
    lines.append("| Result | Test | Customer Journey | What It Proves | Why It Matters | Call To Action | Artifacts |")
    lines.append("|--------|------|------------------|----------------|----------------|----------------|-----------|")
    for case in cases:
        lines.append(
            f"| {case['result']} | `{case['id']}` | {case['journey']} | {case['proves']} | {case['why']} | {case['cta']} | `{case['artifacts']}` |"
        )
        if case["result"] not in {"PASSED", "SKIPPED"}:
            lines.append(f"| ❗ | Details | {case['detail']} |  |  |  |  |")
else:
    lines.append("_No test results collected. Did pytest abort before producing a report?_")

lines.append("")
lines.append("## Notes")
if overall_status == "PASSED":
    lines.append("- All documented customer journeys exercised successfully. Monitor this report for regressions before releases.")
else:
    lines.append("- At least one journey failed. Prioritize remediation before shipping to avoid blocking candidates from practicing.")

report_path.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines[:9]))
if failed:
    print(f"[run_usertests] ⚠️  Failures detected. See full report at {report_path}")
else:
    print(f"[run_usertests] ✅ User test report saved to {report_path}")

PY

echo "[run_usertests] Pytest log saved to ${PYTEST_LOG}"
echo "[run_usertests] Customer-journey report saved to ${SUMMARY_MD}"

exit "${PYTEST_STATUS}"
