# Git History (Derived Audit Trail)

Generated: 2026-06-02T18:08:27+00:00
Repo: `/private/tmp/interview-practice-app-pr17-validation`
Commits: 99

Notes:
- This file is derived from Git commit history (not verbatim customer requests).
- Use this as an adoption baseline before ATHENA audit logs existed.
- For details, inspect commits directly (e.g., `git show <sha>`).

| Date | Commit | Author | Summary |
| --- | --- | --- | --- |
| 2025-02-28T14:49:21-08:00 | `20a935d` | taylor parsons | Initial commit: Interview Practice App setup |
| 2025-10-08T18:49:41-07:00 | `3054d93` | Taylor Parsons | feat: persist interview sessions |
| 2025-10-08T18:55:19-07:00 | `3447776` | Taylor Parsons | docs: add env example and setup guidance |
| 2025-10-08T18:57:33-07:00 | `d05f751` | taylorparsons | Update README.md |
| 2025-10-08T19:07:21-07:00 | `48b2db1` | Taylor Parsons | docs: note chmod for helper scripts |
| 2025-10-08T19:09:32-07:00 | `cedf305` | Taylor Parsons | docs: streamline setup instructions |
| 2025-10-09T15:33:24-07:00 | `1a5471b` | Taylor Parsons | feat: improve logging and session experience |
| 2025-10-09T16:06:01-07:00 | `13a8c88` | Taylor Parsons | docs: capture voice experience feature work |
| 2025-10-09T16:23:53-07:00 | `cfbde58` | Taylor Parsons | chore: remove uploaded artifacts from repo |
| 2025-10-09T16:42:12-07:00 | `52e67ee` | Taylor Parsons | fix: add runtime config and guard run_voice setup |
| 2025-10-09T16:45:32-07:00 | `7b09e7a` | Taylor Parsons | refactor: fold run.sh into voice runner |
| 2025-10-09T16:51:13-07:00 | `2ad2cd4` | Taylor Parsons | docs: fix typo in README |
| 2025-10-10T13:19:28-07:00 | `c6f81bf` | Taylor Parsons | feat: persist dual-side voice transcripts |
| 2025-10-10T20:49:11-07:00 | `8876aea` | Taylor Parsons | feat(voice): input transcription + UI activity + transcript export |
| 2025-10-10T20:53:00-07:00 | `0a3f44b` | Taylor Parsons | docs(prd): reflect server-side input transcription, mic activity UI, browser ASR fallback, transcript export, and role-fidelity tests; add config note and UX requirements |
| 2025-10-10T20:56:38-07:00 | `66cd600` | Taylor Parsons | test(voice): cover realtime session payload for input transcription presence/absence and VAD=none; stub AsyncClient to avoid network; ensure expires_at schema |
| 2025-10-10T20:58:56-07:00 | `ef070fd` | Taylor Parsons | docs(tests): expand test.md with new realtime session tests, targeted runs, coverage, and troubleshooting; clarify offline stubs |
| 2025-10-10T21:00:43-07:00 | `b51aa6a` | Taylor Parsons | test(voice): add VAD threshold parsing test and ensure GET /session includes question_index in voice_messages; docs: update AGENTS.md with policy to cover every MVP feature with tests |
| 2025-10-10T21:01:57-07:00 | `f4bc426` | Taylor Parsons | docs(config): document OPENAI_INPUT_TRANSCRIPTION_MODEL in .env.example and README; mark PRD TODO complete |
| 2025-10-10T21:05:40-07:00 | `2caf9c6` | Taylor Parsons | feat(voice): implement MVP 5 voice selection with preview\n\n- Add app/voice_catalog.json and GET /voices endpoint\n- Persist per-session voice via PATCH /session/{id}/voice with catalog validation\n- Use selected voice_id when creating realtime session\n- UI: add voice selector, preview, and save controls\n- Tests: cover catalog endpoint, set-and-use voice in session, and unknown id rejection\n- PRD TODO: mark implemented items and leave caching/telemetry pending |
| 2025-10-11T11:31:33-07:00 | `0f9d009` | Taylor Parsons | feat(voice-preview): add dynamic preview endpoint with local caching; update catalog to use /voices/preview/{id}; add UI loading state for Preview; add scripts/preseed_voice_previews.py and static voices folder |
| 2025-10-11T12:14:15-07:00 | `e5cb826` | Taylor Parsons | feat(voice/ui): disable browser fallback by default; suppress echo during coach speech; deduplicate finalized user transcripts; preview UX; tests |
| 2025-10-11T13:01:25-07:00 | `3d5b00e` | Taylor Parsons | chore(PR): vendor binary-safe diff and patch series for review; add architecture modularization plan; update PR body with attachments and stack clarification |
| 2025-10-11T13:12:11-07:00 | `04423f2` | Taylor Parsons | merge: voice preview caching + UI fallback off, coach echo suppression, user dedup, and tests |
| 2025-10-11T13:16:18-07:00 | `2affdac` | Taylor Parsons | chore(dev): add scripts/codex_up.sh for one-step venv setup, install, run, tests, and preview pre-seeding (Codex-friendly) |
| 2025-10-11T13:17:25-07:00 | `0a2df7e` | Taylor Parsons | docs: add scripts/codex_up.sh quick-start section with usage, options, and notes |
| 2025-10-11T14:25:11-07:00 | `d3cbdc1` | Taylor Parsons | feat(ui/voice): hide manual input and mic controls during live session; expand transcript viewport; add UI test for layout wiring\n\n- JS: add setVoiceLayout(true/false) to toggle 'Your Answer' textarea, submit/example buttons, and mic button container.\n- JS: expand transcript panel from max-h-64 to max-h-96 while voice is live for readability.\n- Tests: tests/test_ui_voice_layout.py ensures DOM targets exist and layout function is called on start/stop.\n- Rationale: reduce distraction during voice coaching and focus user on the transcript.\n |
| 2025-10-11T14:36:31-07:00 | `5a09097` | Taylor Parsons | feat(coach-level): dual-level prompt (help vs strict) selectable in UI; persisted per session; applied to realtime instructions and evaluations\n\n- Backend: add coach_level to session defaults and payload; PATCH /session/{id}/coach-level; use build_dual_level_prompt() for voice instructions and pass level to evaluation.\n- Prompts: new app/models/prompts.py with dual-level system prompt text.\n- UI: add Coaching Level select + Save; init on load; persist via PATCH; default strict (level_2).\n- Tests: ensure coach-level wired into voice session instructions, and UI selector present + wired.\n |
| 2025-10-11T14:46:00-07:00 | `b996b6c` | Taylor Parsons | feat(voice/ui): coalesce consecutive You messages into a single bubble until Coach speaks\n\n- Add lastFinalSpeaker tracking; set on user/coach finalization.\n- During realtime and hydration, join consecutive user messages into one DOM bubble with newlines.\n- Keep persistence unchanged; this is a display-only aggregation.\n- Maintains dedup + suppression logic; full suite still green. |
| 2025-10-11T14:50:34-07:00 | `9467b44` | Taylor Parsons | fix(voice/ui): continue interim user chunks in the last 'You' bubble to avoid creating a new bubble; coalesce both interim and final user chunks until Coach speaks |
| 2025-10-11T15:03:12-07:00 | `6229c09` | Taylor Parsons | fix(voice/ui): always append user chunks to the last 'You' bubble when the last entry is a finalized user message (structural check)\n\n- Replace reliance on lastFinalSpeaker with DOM/message-structure check to handle varying realtime event orders.\n- Hydration keeps coalescing adjacent user messages.\n- Tests remain green. |
| 2025-10-11T15:06:45-07:00 | `9c5ae0b` | Taylor Parsons | chore(voice/ui): join coalesced 'You' chunks with a space instead of newline for cleaner single-bubble rendering |
| 2025-10-11T15:24:43-07:00 | `c005583` | Taylor Parsons | docs(code): annotate recent local changes with inline comments |
| 2025-10-11T15:27:41-07:00 | `72aaf75` | Taylor Parsons | fix(export): include 'You' lines by merging per-question voice_transcripts for indexes missing candidate messages\n\n- Export now safeguards against sessions where only coach lines were persisted but user transcript exists under voice_transcripts.\n- Leaves existing ordering intact by appending synthetic entries when needed; simple and readable text export with timestamps + roles. |
| 2025-10-11T15:29:13-07:00 | `983f114` | Taylor Parsons | chore(devxp): add commit template + pre-commit guard and installer script\n\n- Template: .github/commit_template.txt prompts for Summary, Rationale, Impact, Testing, Notes.\n- Hook: scripts/hooks/pre-commit blocks code-only commits with no comment lines; BYPASS_COMMENT_CHECK=1 to override.\n- Installer: scripts/install_git_conventions.sh sets commit.template and installs the hook.\n- Docs: README quick-start for conventions. |
| 2025-10-13T15:09:02-07:00 | `d7f3e47` | Taylor Parsons | feat(voice): preview caching endpoint, dedup + export ordering; disable browser ASR fallback by default\n\n- Backend: /voices/preview/{id} endpoint synthesizes and caches MP3 previews; catalog mtime busting.\n- Frontend: fallback OFF and gated start; suppress during coach audio; deduplicate finalized user messages; preview loading state; export transcript ordering + coalescing.\n- Tests: add export transcript unit test (ordering, coalescing, backfill). |
| 2025-10-13T15:45:59-07:00 | `e4d14c3` | taylorparsons | Merge pull request #1 from taylorparsons/feat/voice-preview-fallback-dedup |
| 2025-10-13T15:52:14-07:00 | `2305b70` | Taylor Parsons | docs(readme,test): document voice preview, fallback gating, and export transcript behavior after recent merge |
| 2025-10-13T16:25:44-07:00 | `1ac47b4` | Taylor Parsons | docs(ux): switch SALT blocks to @startsalt/@endsalt and plain code fences |
| 2025-10-13T16:33:01-07:00 | `a3a2351` | Taylor Parsons | docs(ux): extract SALT wireframes into individual .puml files under docs/salt |
| 2025-10-13T16:43:15-07:00 | `82afef2` | Taylor Parsons | docs(ux): add voice submit flow wireframes (CTA + review modal) and update SALT doc |
| 2025-10-13T16:49:36-07:00 | `d219dc6` | Taylor Parsons | feat(voice/ux): add 'Submit Voice Answer' CTA with evaluation flow, enable/disable on transcript readiness |
| 2025-10-13T17:22:23-07:00 | `bf71512` | Taylor Parsons | feat(ux): app bar, question map rail/drawer, sticky footer, sessions modal, in-call voice settings drawer, keyboard shortcuts; keep tests passing |
| 2025-10-13T17:33:18-07:00 | `a041d44` | Taylor Parsons | fix(ux/settings): top Settings opens drawer; hide inline voice settings; wire drawer Preview and Save; reflect saved voice across UI |
| 2025-10-13T17:39:32-07:00 | `483b7de` | Taylor Parsons | feat(voice/ux): after saving voice, offer to restart live session to apply immediately; keep selects in sync |
| 2025-10-13T17:47:15-07:00 | `d317cd1` | Taylor Parsons | docs(ux): add ASCII wireframes and high-level PlantUML doc\n\n- Adds docs/UX_ASCII_WIREFRAMES.md with ASCII wireframes matching SALT layouts (Home, Workspace, Question Map, Voice pre-call/in-call, Feedback, Summary, Sessions, Shortcuts).\n- Adds docs/high.puml for high-level diagrams (for future architecture/flow renders).\n- Complements SALT .puml files under docs/salt and UX_SALT_WIREFRAMES.md which now use @startsalt/@endsalt.\n- Helps reviewers quickly visualize UX without rendering PlantUML.\n |
| 2025-10-14T09:17:34-07:00 | `7e164db` | Taylor Parsons | fix(voice/settings): robust drawer population via shared voices loader; retry + error states; remove dependency on main select; fallback preview URL; consistent select syncing; top Settings uses drawer population |
| 2025-10-14T10:17:26-07:00 | `44c89e3` | Taylor Parsons | docs(demo): add stage branch demo checklist with screenshots guide; link from README |
| 2025-10-14T10:20:42-07:00 | `ddda890` | Taylor Parsons | fix(agent/eval): handle empty/non-JSON model responses without noisy exceptions; add fast-path JSON check, best-effort extraction, and safe fallback fields |
| 2025-10-14T12:16:44-07:00 | `fe51d2c` | Taylor Parsons | docs(eval): capture structured output options, model pricing, and rollout recommendations for gpt-4o/gpt-5 mini+nano |
| 2025-10-14T12:53:50-07:00 | `57c143b` | Taylor Parsons | refactor(voice/settings): move browser ASR + metadata toggles to config; remove UI checkboxes; expose APP_CONFIG defaults; update tests |
| 2025-10-14T13:26:53-07:00 | `c5b2f4d` | Taylor Parsons | docs(readme): document voice fallback/metadata config flags (VOICE_BROWSER_FALLBACK_DEFAULT, VOICE_SHOW_METADATA_DEFAULT) |
| 2025-10-14T14:27:03-07:00 | `0415037` | Taylor Parsons | feat(voice/settings): make drawer the single source of truth; show read-only summary on main page |
| 2025-10-14T14:30:29-07:00 | `4f27067` | Taylor Parsons | fix(voice/settings): prevent reference errors after removing main voice controls |
| 2025-10-14T14:36:58-07:00 | `1b80824` | Taylor Parsons | Revert "fix(voice/settings): prevent reference errors after removing main voice controls" |
| 2025-10-14T14:36:58-07:00 | `eb300cd` | Taylor Parsons | Revert "feat(voice/settings): make drawer the single source of truth; show read-only summary on main page" |
| 2025-10-14T14:36:58-07:00 | `a857176` | Taylor Parsons | Revert "refactor(voice/settings): move browser ASR + metadata toggles to config; remove UI checkboxes; expose APP_CONFIG defaults; update tests" |
| 2025-10-14T15:00:57-07:00 | `2f8d694` | Taylor Parsons | fix(docs): cache resume/job text in state and load via helper so View Docs works offline |
| 2025-10-14T15:13:17-07:00 | `fdee087` | Taylor Parsons | fix(upload): add method=post action=/upload-documents and enctype to form so Start Interview posts even if JS fails |
| 2025-10-14T15:20:44-07:00 | `29f3744` | Taylor Parsons | fix(upload): ignore empty job_description file field; prefer pasted text over file; keep extension validation only when a real file is present |
| 2025-10-14T15:27:16-07:00 | `78d86c4` | Taylor Parsons | fix(ui): remove stale appVoiceConfig reference causing app.js init crash when loading existing sessions |
| 2025-10-14T15:51:35-07:00 | `c497e51` | Taylor Parsons | tests(docs,ui): add upload/UI regression tests; update test.md; minor JS housekeeping |
| 2025-10-14T15:53:25-07:00 | `761f0a4` | taylorparsons | Merge pull request #3 from taylorparsons/stage |
| 2025-10-16T07:36:55-07:00 | `4484bea` | taylorparsons | docs: generalize agent-team roadmap |
| 2025-10-16T07:41:27-07:00 | `52080f4` | taylorparsons | Merge pull request #5 from taylorparsons/codex/refactor-hairiest-file-for-better-isolation |
| 2025-11-24T16:00:51-08:00 | `a774c3c` | taylor parsons | feat: persist voice context and polish interview feedback |
| 2025-11-24T20:28:32-08:00 | `b7beeff` | taylor parsons | chore: tune voice turn detection and feedback formatting |
| 2025-11-25T12:14:54-08:00 | `9f5f55c` | taylor parsons | docs: add langgraph integration plan |
| 2025-11-25T12:22:44-08:00 | `0f50a34` | taylor parsons | docs: add phased voice plan |
| 2025-11-25T12:50:24-08:00 | `4c9f4a5` | taylor parsons | feat: add dual-sided voice transcripts and markdown sanitizer |
| 2025-11-25T13:53:47-08:00 | `118e26e` | taylor parsons | feat: add pdf export and runtime settings ui |
| 2025-11-25T13:54:02-08:00 | `d57bdc8` | taylor parsons | feat: add practice again and settings tests |
| 2025-11-25T14:41:43-08:00 | `2f97aad` | taylor parsons | feat: improve pdf export formatting and summary support |
| 2025-11-26T11:08:06-08:00 | `2c2cd0b` | taylor parsons | feat: enforce evaluation schema and persist summaries |
| 2025-11-26T11:56:36-08:00 | `85f9d7f` | taylor parsons | feat: manage questions mid-session and add gpt-realtime voice |
| 2025-11-26T11:57:58-08:00 | `98aa27c` | taylor parsons | docs: add question management and gpt-realtime voice notes |
| 2025-11-26T12:10:06-08:00 | `cffcb59` | taylor parsons | test: enforce gpt-realtime in voice catalog |
| 2025-11-26T12:24:53-08:00 | `3052944` | taylor parsons | feat: add realtime voice model selector |
| 2025-11-26T12:34:00-08:00 | `4714754` | taylor parsons | feat: format plain example answers with bold key sentences |
| 2025-11-26T13:30:14-08:00 | `3ce1958` | taylor parsons | feat: add question follow-ups and display in UI |
| 2025-11-26T14:29:35-08:00 | `85f5504` | taylor parsons | feat: voice button states, keep example visible, cache example answers, show follow-ups |
| 2025-11-26T14:47:13-08:00 | `e4048d1` | taylor parsons | tweak example answer prompt for concrete AI actions |
| 2025-12-30T14:09:10-08:00 | `3d4fba5` | taylor parsons | feat: make STAR+I conditional by question type |
| 2025-12-30T14:24:04-08:00 | `8fbbb97` | taylor parsons | test: update evaluation stub for question type |
| 2025-12-30T14:35:40-08:00 | `33241fb` | taylor parsons | chore: update deps for security fixes |
| 2025-12-30T14:44:21-08:00 | `bfca2cc` | taylor parsons | chore: bump python-dotenv |
| 2025-12-30T16:17:11-08:00 | `78f0697` | taylor parsons | chore: bump pypdf |
| 2026-01-07T18:45:37-08:00 | `1b68b46` | D. Taylor Parsons III | chore: add MIT license |
| 2026-01-09T15:23:53-08:00 | `0758ba3` | taylor parsons | chore: add security tooling |
| 2026-01-09T15:24:32-08:00 | `7347629` | taylor parsons | chore: restore codex_up.sh permissions |
| 2026-01-09T15:53:38-08:00 | `7969cb6` | taylor parsons | chore: bump pypdf to 6.6.0 |
| 2026-01-09T16:47:30-08:00 | `cb6b74e` | taylor parsons | fix: retry pdf parsing in non-strict mode |
| 2026-01-09T21:00:04-08:00 | `d68cb60` | taylor parsons | test: cover voice catalog endpoints |
| 2026-01-10T08:52:36-08:00 | `4c7c633` | taylor parsons | docs: mark voice plan progress |
| 2026-01-10T11:06:20-08:00 | `e8faaef` | taylor parsons | ci: gate security checks by file presence |
| 2026-01-10T11:34:49-08:00 | `e7ec4df` | taylor parsons | chore: retrigger security workflow |
| 2026-01-10T12:03:13-08:00 | `055eb70` | taylor parsons | fix: skip venv and self in secret scan |
| 2026-01-10T13:32:51-08:00 | `5dd2cef` | taylor parsons | fix: reduce security audit false positives |
| 2026-01-24T14:19:26-08:00 | `665af4c` | taylor parsons | docs: add voice coach turn-taking design |
