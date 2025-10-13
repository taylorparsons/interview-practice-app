# UX Wireframes (PlantUML SALT)

This document contains lightweight wireframes for the updated app flow using PlantUML SALT. Copy any block into a PlantUML renderer (e.g., extensions, https://www.plantuml.com/plantuml/) to preview.

Render tips
- Each block is standalone between `@startsalt … @endsalt`.
- SALT focuses on layout; labels imply behavior. Group boxes name functional areas.

---

## A. Home (Start or Resume)

```
@startsalt
{
  {T} Interview Practice App — Home

  "Resume Session" {
    [Saved sessions ▼] | [ Load ] [ Delete ]
    [Rename selected session ____________________________] | [ Rename ]
  }

  --

  "Start New Interview" {
    [Resume (PDF/DOCX/TXT)] | [ Choose File ]
    [Job Description (PDF/DOCX/TXT)] | [ Choose File ]
    [Or paste job description text here …........................................]
    [ Start Interview Practice ]
  }
}
@endsalt
```

---

## B. Interview Workspace (Option A: App Bar + Left Question Rail)

```
@startsalt
{
  "Top Bar" {
    [ New Interview ] | [ Sessions ▼ ] | [ Settings ⚙ ] | "Session: ai_product_manager_submitted_resume" | "Question 1 of 5" | [ View Docs ]
  }

  --

  "Workspace" {
    "Question Map (left rail)" {
      * 1  • Not started
      * 2  • In progress
      * 3  ✓ Answered
      * 4  ○ Review
      * 5  • Not started
      [ Filter: (All ▼) ]
    } |
    "Main Panel" {
      {T} Question
      [Can you describe a specific situation … ?]
      --
      {T} Your Answer
      [........................................................................]
      [........................................................................]
      [ Submit Answer ] [ See Example Answer ]
      --
      {T} Voice Interview Coach (collapsible)
      [ Start Voice Session ] [ Export Transcript ]  "Mic idle"
      () Browser transcription fallback  [ ]  | "Coaching Level" [ Help ▼ ] [ Save ]
      "Voice" [ Verse ▼ ] [ Preview ] [ Save ]
      [--- Transcript will appear here once the session starts ---]
    }
  }

  --

  "Footer (sticky)" {
    [ ◀ Prev ] | [ Next ▶ ] | [ Mark for review ] | [ Export Transcript ]
  }
}
@endsalt
```

---

## C. Question Map (Compact Drawer / Mobile)

```
@startsalt
{
  {T} Questions
  [ Search ______________________________________ ]
  --
  * 1  ✓  "Tell me about yourself"            (Answered)
  * 2  •  "Stakeholder alignment example"     (In progress)
  * 3  ○  "Conflict you resolved"             (Review)
  * 4  •  "Impact you delivered"              (Not started)
  * 5  •  "Long‑term goals"                   (Not started)
  --
  [ Filter: (All ▼) ]  [ Close ]
}
@endsalt
```

---

## D. Voice — Pre‑Call Settings (visible before start)

```
@startsalt
{
  {T} Voice Coach — Pre‑Call
  "Mic & Transport" {
    "Status:"  {T} Mic idle
    [ Start Voice Session ]
  }
  --
  "Session Settings" {
    () Browser transcription fallback  [ ]
    () Show transcript metadata        [ ]
    "Coaching Level" [ Help ▼ ] [ Save ]
    "Voice" [ Verse ▼ ] [ Preview ] [ Save ]
  }
  --
  [ Transcript will appear here once the session begins ]
}
@endsalt
```

---

## E. Voice — In‑Call Minimal Controls (settings moved to drawer)

```
@startsalt
{
  {T} Voice Coach — Live
  "Controls" {
    [ Stop Voice Session ] | [ Mute ] | {T} Live | [ Export Transcript ] | [ ⚙ Settings ]
  }
  --
  "Transcript" {
    {T} COACH  — Hello and welcome …
    {T} YOU    — My experience …
    {T} COACH  — Thanks. Try structuring with STAR …
  }
  --
  "Settings Drawer (on ⚙)" {
    () Browser transcription fallback  [ ]
    () Show transcript metadata        [ ]
    "Coaching Level" [ Help ▼ ] [ Save ]
    "Voice" [ Alloy ▼ ] [ Preview ] [ Save ]
    [ Close ]
  }
}
@endsalt
```

---

## F. Feedback View (after submit)

```
@startsalt
{
  {T} Feedback — Question 2 of 5
  "Score" {
    {T} Overall Score: 5 / 10  | [ Progress ▓▓░░░ ]
  }
  --
  "Highlights" {
    {T} Strengths
    [ • Clear outcomes • Collaboration ]
    {T} Areas for Improvement
    [ • Add metrics • Clarify context ]
  }
  --
  "Content Feedback" {
    [ STAR breakdown, actionable suggestions, examples … ]
  }
  --
  "Tone Feedback" {
    [ Empathetic, concise, confident … ]
  }
  --
  "Your Typed Answer" {
    [ (readonly) Your submitted text … ]
  }
  --
  [ ◀ Prev ] | [ Next Question ▶ ] | [ Mark for review ]
}
@endsalt
```

---

## G. Summary Screen

```
@startsalt
{
  {T} Interview Summary
  "Overview" {
    {T} Session: ai_product_manager_submitted_resume
    {T} Completed: 5 of 5
    [ Export Transcript ] [ Download Summary ]
  }
  --
  "Per‑Question Cards" {
    * Q1  ✓  Score 7/10  [ View ]
    * Q2  ✓  Score 5/10  [ View ]
    * Q3  ✓  Score 6/10  [ View ]
    * Q4  ✓  Score 8/10  [ View ]
    * Q5  ✓  Score 7/10  [ View ]
  }
  --
  [ Practice Again ] | [ Return Home ] | [ New Interview ]
}
@endsalt
```

---

## H. Global Sessions List

```
@startsalt
{
  {T} Sessions
  [ Search ______________________________________ ]
  --
  "Saved" {
    * ai_product_manager_submitted_resume   • 5 q  • Updated 2h ago   [ Load ] [ Rename ] [ Delete ]
    * ds_lead_enterprise                     • 7 q  • Updated 1d ago   [ Load ] [ Rename ] [ Delete ]
    * swe_fullstack_cloud                    • 5 q  • Updated 3d ago   [ Load ] [ Rename ] [ Delete ]
  }
  --
  [ New Interview ] | [ Close ]
}
@endsalt
```

---

## I. Keyboard Shortcuts (Legend)

```
@startsalt
{
  {T} Shortcuts
  [ J / ← ] | {T} Previous question
  [ K / → ] | {T} Next question
  [ V ]     | {T} Start/Stop voice
  [ M ]     | {T} Mute/Unmute
  [ E ]     | {T} Export transcript
  [ G ]     | {T} Open Question Map
}
@endsalt
```
