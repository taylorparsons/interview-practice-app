# Frontend Manual Checklist (Phase 1)

Use this checklist to verify dual-sided transcripts, formatting, and mic UX:

- Start a voice session and speak; confirm timeline shows both “Coach” and “You” entries in real time and scrolls to the bottom (freeze toggle off).
- Confirm coach messages preserve Markdown formatting (lists/paragraphs); no raw `<script>` is rendered.
- Toggle “Browser ASR fallback” and “Show metadata”; metadata appears only when enabled.
- Mic indicator cycles through idle → listening → speaking; when mic permission is denied, indicator shows `muted`.
- Export transcript (JSON/txt) produces both roles.
- Export PDF (Summary → Export PDF) downloads a file with questions/evaluations/transcripts.
