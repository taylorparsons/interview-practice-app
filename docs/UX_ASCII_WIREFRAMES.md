# UX Wireframes (ASCII)

These lightweight, implementation‑agnostic wireframes illustrate the proposed navigation and UI flow. Copy/paste a block into any Markdown viewer with a monospace font to preview.

Legend: [Button], (Toggle), {Status}, ▼ dropdown, ✓ checked, • bullet, ○ hollow.

---

## A. Home — Start or Resume

```
+================================================================================+
|                            Interview Practice App — Home                       |
+================================================================================+
|                                                                                |
|  ┌────────────────────────────── Resume Session ─────────────────────────────┐  |
|  |  Saved sessions: [ ai_product_manager_submitted_resume ▾ ]  [Load] [Delete]|  |
|  |  Rename: [__________________________________________]              [Rename] |  |
|  └───────────────────────────────────────────────────────────────────────────┘  |
|                                                                                |
|  ┌──────────────────────────── Start New Interview ──────────────────────────┐  |
|  |  Resume (PDF/DOCX/TXT):            [ Choose File ]                         |  |
|  |  Job Description (PDF/DOCX/TXT):   [ Choose File ]                         |  |
|  |  Or paste JD text:  [ Paste up to a few thousand characters here... ]     |  |
|  |                                                                           |  |
|  |                          [ Start Interview Practice ]                      |  |
|  └───────────────────────────────────────────────────────────────────────────┘  |
|                                                                                |
+================================================================================+
```

---

## B. Interview Workspace — App Bar + Left Question Rail

```
+================================================================================+
|  [ New Interview ]  [ Sessions ▾ ]  [ Settings ⚙ ]  Session: ai_prod...  Q 1/5 |
|  ----------------------------------------------------------------------------- |
|  View Docs                                                                    |
+------------+-------------------------------------------------------------------+
| Questions  |  ┌──────────── Question ────────────┐                             |
|  All ▾     |  | Can you describe a specific ...  |                             |
|            |  └──────────────────────────────────┘                             |
|  1 •       |  ┌─────────── Your Answer ──────────┐                            |
|  2 •       |  |                                    |                           |
|  3 ✓       |  |                                    |                           |
|  4 ○       |  └────────────────────────────────────┘                           |
|  5 •       |  [ Submit Answer ]   [ See Example Answer ]                       |
|            |                                                                   |
|  Filter:   |  ┌───── Voice Interview Coach (collapsible) ─────┐               |
|   (All)    |  | [ Start Voice Session ]  [ Export Transcript ] |  {Mic idle}   |
|            |  | ( ) Browser ASR fallback   Coaching: [Help ▾]  | [Save]        |
|            |  | Voice: [ Verse ▾ ] [Preview] [Save]            |               |
|            |  | --- Transcript appears here when session starts ---            |
|            |  └──────────────────────────────────────────────────┘             |
+------------+-------------------------------------------------------------------+
|  ◀ Prev                 [ Mark for review ]                     Next ▶         |
+================================================================================+
```

---

## C. Question Map — Drawer (Mobile / Compact)

```
+------------------------------- Questions --------------------------------+
|  Search: [____________________________________]  [Close]                  |
|  1  ✓  Tell me about yourself              (Answered)                     |
|  2  •  Stakeholder alignment example       (In progress)                  |
|  3  ○  Conflict you resolved               (Review)                        |
|  4  •  Impact you delivered                (Not started)                   |
|  5  •  Long‑term goals                     (Not started)                   |
|  Filter: [ All ▾ ]                                                          |
+----------------------------------------------------------------------------+
```

---

## D. Voice — Pre‑Call Settings (visible before start)

```
+------------------------------- Voice Coach — Pre‑Call -------------------------+
|  {Status} Mic idle                 [ Start Voice Session ]                     |
|-------------------------------------------------------------------------------|
|  ( ) Browser transcription fallback        ( ) Show transcript metadata       |
|  Coaching Level: [ Help ▾ ] [ Save ]                                          |
|  Voice: [ Verse ▾ ]  [ Preview ]  [ Save ]                                    |
|-------------------------------------------------------------------------------|
|  Transcript will appear here once the session begins.                          |
+-------------------------------------------------------------------------------+
```

---

## E. Voice — In‑Call Minimal Controls (settings in drawer)

```
+------------------------------- Voice Coach — Live -----------------------------+
|  [ Stop Voice Session ]  [ Mute ]  {Live}  [ Export Transcript ]  [ ⚙ ]       |
|-------------------------------------------------------------------------------|
|  COACH: Hello and welcome...                                                  |
|  YOU  : My experience...                                                      |
|  COACH: Thanks. Try structuring with STAR...                                  |
|-------------------------------------------------------------------------------|
|  ⚙ Settings Drawer →  ( ) Browser ASR  ( ) Show metadata                      |
|                      Coaching: [ Help ▾ ] [ Save ]                             |
|                      Voice: [ Alloy ▾ ] [ Preview ] [ Save ]                  |
|                      [ Close ]                                                |
+-------------------------------------------------------------------------------+
```

---

## F. Feedback View

```
+-------------------------------- Feedback — Question 2/5 ----------------------+
|  Overall Score: 5/10                    Progress: [▓▓░░░]                    |
|-------------------------------------------------------------------------------|
|  Strengths                     |  Areas for Improvement                       |
|  • Clear outcomes              |  • Add metrics                               |
|  • Collaboration               |  • Clarify context                           |
|-------------------------------------------------------------------------------|
|  Content Feedback                                                             |
|  STAR breakdown, actionable suggestions, examples…                             |
|-------------------------------------------------------------------------------|
|  Tone Feedback                                                                |
|  Concise, confident…                                                          |
|-------------------------------------------------------------------------------|
|  Your Typed Answer (read‑only)                                                |
|  “...user’s submitted text...”                                                |
|-------------------------------------------------------------------------------|
|  ◀ Prev                                         [ Next Question ]             |
+-------------------------------------------------------------------------------+
```

---

## G. Summary Screen

```
+-------------------------------- Interview Summary -----------------------------+
|  Session: ai_product_manager_submitted_resume      Completed: 5 / 5            |
|  [ Export Transcript ]   [ Download Summary ]                                   |
|-------------------------------------------------------------------------------|
|  Per‑Question Cards                                                             |
|  ▸ Q1  ✓  Score 7/10   [ View ]                                                |
|  ▸ Q2  ✓  Score 5/10   [ View ]                                                |
|  ▸ Q3  ✓  Score 6/10   [ View ]                                                |
|  ▸ Q4  ✓  Score 8/10   [ View ]                                                |
|  ▸ Q5  ✓  Score 7/10   [ View ]                                                |
|-------------------------------------------------------------------------------|
|  [ Practice Again ]   [ Return Home ]   [ New Interview ]                      |
+-------------------------------------------------------------------------------+
```

---

## H. Sessions List (Global)

```
+------------------------------------ Sessions ----------------------------------+
|  Search: [___________________________________________]                         |
|-------------------------------------------------------------------------------|
|  ai_product_manager_submitted_resume   • 5 q  • Updated 2h   [Load][Ren][Del]  |
|  ds_lead_enterprise                    • 7 q  • Updated 1d   [Load][Ren][Del]  |
|  swe_fullstack_cloud                   • 5 q  • Updated 3d   [Load][Ren][Del]  |
|-------------------------------------------------------------------------------|
|  [ New Interview ]   [ Close ]                                                 |
+-------------------------------------------------------------------------------+
```

---

## I. Keyboard Shortcuts

```
+------------------------------- Shortcuts --------------------------------------+
|  J / ←   Previous question                                                     |
|  K / →   Next question                                                         |
|  V       Start/Stop voice                                                      |
|  M       Mute/Unmute                                                           |
|  E       Export transcript                                                     |
|  G       Open Question Map                                                     |
+-------------------------------------------------------------------------------+
```

---

## Notes on the Requested Improvements
- “New Interview” CTA is always visible in the top bar (no refresh needed).
- Question navigation is provided via the left rail and mobile drawer; both support jump & filter.
- Voice settings are visible only pre‑call; during a call they move to a settings drawer, leaving minimal in‑call controls.

