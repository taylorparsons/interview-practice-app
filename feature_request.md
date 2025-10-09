# Feature Request — Improve Voice-to-Text Coach UX

## Summary
- Capture the candidate’s spoken transcript in the realtime voice coaching timeline so the dialog always includes both “Coach” and “You” entries.
- Persist those voice transcripts with the rest of the session payload so resuming a saved session restores the full conversation.
- Render coach responses with preserved line breaks (paragraphs, numbered prompts, example answers) so candidates can practice repeating the guidance verbatim.

## Problem / Opportunity
- Today only the coach text reliably shows up in the voice panel. Candidate utterances are hard to review or disappear when the page reloads, making practice iterations difficult.
- The coach’s long-form guidance collapses into one dense block, which is hard to read aloud or mimic.
- A clearer transcript history would help candidates rehearse, revisit, or share progress while aligning UX with the text-based workflow.

## Requirements
1. Show user voice transcripts inline with the coach feed in realtime (no page refresh required).
2. Persist both sides of the voice dialog to the session JSON so reload/resume flows recover the history.
3. Preserve and display coach formatting (paragraphs, numbered items, quoted examples) instead of collapsing everything into a single paragraph.
4. Ensure “Practice Again” surfaces once all questions are completed (typed or voice) and shows detailed post-interview analysis for voice sessions.
5. When “Practice Again” is chosen, let candidates (a) revisit the existing question set or (b) append new questions they didn’t cover previously.
6. Offer model selection so candidates can swap between `gpt-4o-mini` (default), `gpt-5-mini`, and full `gpt-5`, including per-session controls for “thinking effort” (medium/high) and “verbosity” (low/medium/high) that remain adjustable mid-interview.
7. Let candidates choose the realtime coach voice from a preset list (e.g., Verse, Alloy, Ash, Ballad, Cedar, Coral, Echo, Marin, Sage, Shimmer) directly on the interview page, with quick preview playback.
8. Provide an “Export as PDF” study guide that captures the full interview summary, voice dialog, and key takeaways in a clean layout candidates can review offline.
9. Support existing sessions without migration failures—fall back gracefully when older data lacks voice transcripts.

## Desired UX Examples
```
Coach
Let's set the record straight. Your resume states you're an AI product and program leader, own that. ...
Ready?
Answer one:
"Transaction: In my role as a City AI Officer..."

Answer two:
"I played a pivotal role..."

Let's refine them further—go ahead and repeat back or choose, and we'll perfect it.

You
I'd lean into the City AI Officer example because it shows measurable impact...
```
> Note: preserve blank lines and headings (“Coach”, “You”) to keep the dialog scannable.

## Acceptance Criteria
- [ ] Voice transcript entries appear in the UI for both agent and user during live sessions.
- [ ] Resuming or reloading a session restores all prior voice exchanges with original formatting.
- [ ] Coach messages show paragraph spacing that matches the text provided by the agent.
- [ ] QA covers both new sessions and older session files lacking the new fields.

## Notes / Implementation Ideas
- Reuse or extend the `voice_transcripts` structure already persisted in `session_store/*.json`.
- Consider adding a richer message object (role, text, timestamps) when storing voice events.
- Ensure any migrations happen lazily when sessions are loaded to avoid blocking startup.
- “Practice Again” should reset state while preserving artifacts (questions, transcripts, evaluations), and expose an “Add Questions” flow to capture new prompts before restarting.
- Add a front-end selector that defaults to `gpt-4o-mini` but can switch to `gpt-5-mini`/`gpt-5` and tweak effort/verbosity, writing the choice to the session so backend requests honor it.
- Add a voice selector UI (dropdown with play buttons) mirroring the provided design; persist the chosen voice and pass it when creating realtime sessions.
- For the PDF export, evaluate server-side generation (e.g., WeasyPrint) vs. client-side rendering; include a summary page plus per-question cards and full transcript appendix.
