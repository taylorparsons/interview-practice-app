# Running the Test Suite

1. **Create/activate virtual env (if needed)**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Execute the tests**
   ```bash
   pytest -vv --maxfail=1 --durations=5
   ```
   - Uses the FastAPI TestClient to simulate voice message persistence.
   - Emits per-test names and shows the five slowest tests for easier debugging.
   - Verifies candidate and coach transcript entries are stored and retrievable.
   - Confirms completeness metrics log once both roles appear.

Or simply run:
```bash
./run_tests.sh
```
This script prints the command being used and mirrors the detailed pytest output.

3. **Review output**
   - `..` indicates passing tests; any failure will show stack traces for investigation.
   - Warnings about PyPDF2 are expected; follow-up separately if you plan to migrate to `pypdf`.

## Observability Follow-Up
- Subscribe your log pipeline to `voice.transcript.metric` to monitor completeness ratios.
- Trend the `candidate_count` and `coach_count` fields to ensure both sides stay populated across sessions.
- Monitor latency during real sessions to keep transcript rendering under the 150 ms target.
