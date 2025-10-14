# Demo: Voice Settings Drawer + UX (stage)

This checklist verifies the voice settings drawer, fallback preview, save + immediate apply, and navigation updates introduced on the `stage` branch.

- Audience: product/QA
- Scope: web UI + FastAPI local dev
- Pre-reqs: server running, `.env` with `OPENAI_API_KEY` for previews (optional), some saved sessions for switching tests

## Quick Start
- Start server: `./run_voice.sh` (or `scripts/codex_up.sh --start`)
- Open: http://localhost:8000/
- Recommended: open DevTools Network tab to simulate failure for retry tests

## Demo Checklist

1) Drawer loads voices (no race with main)
- Click Settings (top bar or in coach panel) immediately after page load
- Expect: drawer opens, shows “Loading voices…”, then the voice list appears
- No dependency on main select; both populate reliably

2) Error + Retry state for voices
- In DevTools → Network → toggle Offline and open Settings
- Expect: drawer shows “Failed to load voices.” and a “Retry loading voices” button
- Turn Offline OFF, click Retry → drawer repopulates with voices

3) Voice preview works (with fallback)
- In drawer: select a voice, click Preview
- Expect: audio plays; if preview_url missing, route falls back to `/voices/preview/{id}`
- Repeat from main selector Preview to confirm parity

4) Save voice selection (no session live)
- In drawer (or main), click Save
- Expect: success notice; both selects show the saved voice; starting a new voice session uses this voice

5) Save voice selection (session live → immediate apply)
- Start Voice Session → Settings → change voice → Save
- Expect: prompt “Restart the voice session now to apply the new voice?”
- Click OK → session stops and restarts; the new voice is active

6) Submit Voice Answer
- Speak an answer; when “Submit Voice Answer” enables, click it
- Expect: feedback view renders, same as typed Submit behavior

7) Question navigation + review marks
- Use the left rail or Questions drawer (mobile) to jump; status shows In progress / Answered / Review
- Use sticky footer (Prev / Mark for review / Next) and keyboard shortcuts (J/K or ←/→)

8) Sessions modal workflow
- Click Sessions (top bar) → search, Load, Rename, Delete; Refresh updates the list
- Loading a session updates the header session name and question position

## Expected Screenshots
Place screenshots under `pr_assets/screenshots/stage/` using the names below (or attach in PR):

1. `01_settings_loading.png` — Drawer open with “Loading voices…”
2. `02_settings_failed_retry.png` — Drawer showing failure + Retry button
3. `03_settings_loaded.png` — Drawer populated, standard state
4. `04_preview_drawer.png` — Drawer preview playing (voice preview audio visible)
5. `05_save_not_live.png` — Save success (hint text), no restart prompt
6. `06_save_live_prompt.png` — Restart prompt shown while live
7. `07_after_restart.png` — Live state after restart (new voice active)
8. `08_submit_voice_answer.png` — Feedback panel after voice submit
9. `09_question_rail.png` — Left rail with statuses and current selection highlight
10. `10_sessions_modal.png` — Sessions modal with search + actions visible

Each screenshot should include the relevant control and any status text (e.g., “Loading voices…”, failure message, restart prompt).

## Notes / Tips
- If previews 503 (no API key), the buttons remain functional but will show a failure dialog; route health is tested by the unit suite.
- Logs: `logs/app.log` includes realtime session creation and previews; use for correlation during live restarts.
- Keyboard shortcuts: J/→ Next, K/← Prev, V Start/Stop, M Mute/Unmute, E Export, G Open Questions.

## Acceptance
- Drawer works even if opened before `/voices` completes.
- Drawer shows failure + Retry when `/voices` errors; Retry repopulates on success.
- Preview works in both main and drawer; fallback route covers missing preview_url.
- Save updates both selects; live restart prompt applies new voice immediately when confirmed.
- Submit Voice Answer produces feedback with no errors.
- Question rail and Sessions modal behave as documented.

