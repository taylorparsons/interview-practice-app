# Voice Coach Turn-Taking + Feedback Policy (Voice Only)

Date: 2026-01-24
Status: Proposed

## Context
User feedback shows the realtime voice coach interrupts candidates mid-thought and repeats partial rewrites instead of listening through, creating a frustrating loop. We need the voice coach to listen longer, evaluate completeness, and only offer examples or scores when invited.

## Goals
- Reduce interruptions during voice answers by waiting longer and honoring "more time" requests.
- Evaluate completeness before replying; ask for missing details when needed.
- Offer full example answers only when the candidate opts in.
- Offer a score only when enough information exists, and only if the candidate wants it.
- Prevent repetitive refinement loops.

## Non-goals
- Changing text (typed) coach behavior.
- Reworking evaluation scoring or question generation.
- Adding heavy UI controls or new modes.

## Voice-only policy (behavior spec)
1) Listen first, assess completeness.
- If the answer is complete: ask once, "Want a full example answer?" If yes, provide one complete example and stop; if no, move on.
- If the answer is incomplete: ask 1-2 specific missing details (e.g., impact, actions taken, metrics).

2) Ask-before-example.
- Do not provide full rewritten answers unless the candidate asks for it.

3) Time requests.
- If the candidate says "give me a second" / "let me think" / "one moment": respond once with "Take your time—I'm listening" and wait silently until they continue or say they are done.

4) Done cues.
- Treat "I'm done" / "that's it" / "that should cover it" as completion signals and proceed.

5) Optional scoring.
- If enough info exists to score, ask once: "Want a quick score (1-10)?"
- If yes: provide the score and a single, concise improvement to raise the score; then ask if they want help improving.
- If no: move on without repeating the offer.

6) No nagging.
- Do not repeat the same request more than once per turn.

## Implementation plan (Option A)
- Update realtime voice instructions in `app/main.py` `_build_voice_instructions` with the policy block above.
- Adjust the initial realtime `response.create` instruction in `app/static/js/app.js` to align with ask-before-example + wait-for-time requests.
- Increase server-side VAD silence duration in `app/config.py` (`OPENAI_TURN_SILENCE_MS`) to reduce interruptions (target: ~1800–2000ms; remain configurable via env).
- Keep all changes voice-only; no typed coach prompt changes.

## Logging
- Emit a structured log when voice session is created that includes VAD settings and a short policy tag so we can verify the right behavior is in use.

## Testing
- Add/extend tests in `tests/test_voice_session.py` to assert updated VAD defaults and the policy block in the instructions payload.
- Add a voice prompt regression check in `tests/test_coach_level.py` to ensure voice policy language is present for `level_1` (and unchanged for text).

## Acceptance criteria
- Coach does not interrupt during typical pauses; waits longer before responding.
- Coach does not provide full examples unless asked.
- Coach asks for missing details when answers are incomplete.
- Coach offers a score only if enough information exists and only after asking.
- No repeated refinements without the candidate asking for more help.

## Risks / follow-ups
- Model compliance risk: If the realtime model does not consistently honor waiting cues, consider adding a client-side "I'm done" trigger in a follow-up iteration.
