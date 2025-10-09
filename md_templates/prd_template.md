# Product Requirements Document (PRD)
# {{Project Name}}

Project: {{project_slug}}
Owner: {{owner_name}}
Date Created: {{YYYY-MM-DD}}
Status: {{Draft | In Review | Approved}}
Version: {{major.minor}}

---

## Executive Summary

One-paragraph overview of the product’s purpose, the problem it solves, and the outcome it enables.

Core Value Proposition:
- {{Value #1}}
- {{Value #2}}
- {{Value #3}}

---

## Problem Statement

### Current Pain Points
- {{Pain point 1}}
- {{Pain point 2}}
- {{Pain point 3}}
- {{Pain point 4}}

### Why Now
- {{Market/Timing reason 1}}
- {{User demand / cost / risk}}

---

## Success Criteria

### Must Have (MVP)
Functional Requirements:
1. {{Requirement 1}}
2. {{Requirement 2}}
3. {{Requirement 3}}

Non-Functional Requirements:
1. {{Privacy/Security}}
2. {{Performance target}}
3. {{Reliability/Availability}}
4. {{Maintainability/Operability}}
5. {{UX baseline}}

Success Metrics:
- {{Metric}} → Target: {{value}} by {{date}}
- {{Metric}} → Target: {{value}} by {{date}}

### Should Have (Phase 2)
- {{Feature}}
- {{Feature}}

### Could Have (Phase 3)
- {{Feature}}
- {{Feature}}

### Won’t Have (Out of Scope)
- {{Out-of-scope item}}
- {{Out-of-scope item}}

---

## User Personas & Use Cases

### Primary Persona: {{Persona Name}}
Background:
- Role: {{role}}
- Context: {{environment/tools}}
- Goals: {{goal 1}}, {{goal 2}}
- Pain: {{primary pain}}

Key Use Cases (Template):
Use Case {{N}}: {{Short name}}
```
Scenario: "{{Trigger/question}}"
Current State: {{How it’s done today}}
Desired State:
1. {{Step}}
2. {{Step}}
3. {{Step}}
Outcome: {{Measurable result}}
```

(Repeat for 3–5 core use cases)

---

## System Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────┐
│               DATA SOURCES                  │
├─────────────────────────────────────────────┤
│ • {{Source A}} • {{Source B}} • {{Source C}}│
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│            PROCESSING PIPELINE              │
├─────────────────────────────────────────────┤
│ 1. {{Stage 1}} 2. {{Stage 2}} 3. {{Stage 3}}│
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│                DATA STORE                   │
├─────────────────────────────────────────────┤
│ • {{DB/Index/Cache}}                        │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│              USER INTERFACES                │
├─────────────────────────────────────────────┤
│ • {{UI #1}} • {{UI #2}} • {{UI #3}}         │
└─────────────────────────────────────────────┘
```

### Core Components
1. {{Component Name}} — Responsibilities, inputs/outputs, key decisions
2. {{Component Name}} — Responsibilities, inputs/outputs, key decisions
3. {{Component Name}} — Responsibilities, inputs/outputs, key decisions

---

## Data Requirements

### Entity Schema (Adapt per domain)
```json
{
  "id": "{{unique_id}}",
  "type": "{{entity_type}}",
  "name": "{{display_name}}",
  "created_at": "{{ISO-8601}}",
  "updated_at": "{{ISO-8601}}",
  "source": "{{system_of_record}}",
  "attributes": { "key": "value" },
  "relationships": [ { "to": "{{entity_id}}", "type": "{{rel_type}}", "weight": 0.0 } ],
  "metadata": {}
}
```

### Relationship Schema (Optional)
```json
{
  "source": "{{id}}",
  "target": "{{id}}",
  "type": "{{relationship_category}}",
  "weight": {{0.0-1.0}},
  "created_at": "{{ISO-8601}}",
  "why": ["{{reason-code}}"],
  "metadata": {}
}
```

### Data Constraints
- Required fields: {{list}}
- Indexing: {{indexes for queries}}
- Retention: {{policy}}

---

## Technical Constraints

### Platform
- OS/Runtime: {{e.g., macOS, Linux, iOS, Web}}
- Deployment: {{Local | Cloud | Hybrid}}
- Storage: {{Local disk | Managed DB}}
- Processing: {{Local-first | Cloud-first}}

### Technology Stack (Recommendations)
Backend:
- Language/Runtime: {{e.g., Python/Node/Go}}
- Framework: {{e.g., Flask/FastAPI/Express}}
- Database: {{e.g., SQLite/Postgres/NoSQL}}
- Messaging/Jobs: {{e.g., Celery/SQS/Resque}}

Frontend:
- Framework: {{e.g., React/Vue/Vanilla}}
- Visualization/UI: {{e.g., D3/Charting lib/Design system}}
- Hosting: {{Static server/SPA}}

### Performance Targets
- {{Operation}}: {{latency}} p95
- {{Throughput}}: {{N ops/sec}}
- {{Batch job}}: completes in {{time}} for {{size}}

### Storage Targets
- Total footprint: ~{{size}} at {{scale}}
- Growth: {{rate}}/month
- Indexes: {{size}} at {{scale}}

---

## Dependencies & Integrations

Platform/OS:
- {{File system APIs / Permissions}}
- {{System services}}

Libraries:
- {{lib name}} — {{purpose}}
- {{lib name}} — {{purpose}}

External APIs (Optional):
- {{Provider}} — {{usage}} — {{rate limits/costs}}
- {{Provider}} — {{usage}}

---

## Security & Privacy

Privacy Requirements:
1. {{Data handling/PII policy}}
2. {{Local vs cloud processing}}
3. {{Telemetry policy}}
4. {{Encryption at rest/in transit}}

Data Access:
- Read: {{scopes}}
- Write: {{scopes}}
- No modification of {{constraints}}

Permissions Required:
- {{OS permissions/app entitlements}}

Threats & Controls:
- {{Threat}} → {{Control}}
- {{Threat}} → {{Control}}

---

## User Experience Requirements

Design Principles:
1. {{Principle 1}}
2. {{Principle 2}}
3. {{Principle 3}}

UI Requirements:
1. {{Primary interface elements}}
2. {{Navigation / IA}}
3. {{Theming/Accessibility}}

Sample UX Flows:
- {{Flow name}}: Steps 1–4 with outcome
- {{Flow name}}: Steps 1–4 with outcome

---

## Risks & Mitigation

Technical Risks
- Risk: {{description}}
  - Mitigation: {{approach}}
- Risk: {{description}}
  - Mitigation: {{approach}}

User Experience Risks
- Risk: {{description}}
  - Mitigation: {{approach}}
- Risk: {{description}}
  - Mitigation: {{approach}}

---

## Timeline & Milestones

Option A — Aggressive 2-Week Plan
- Week 1: {{core system components}}
- Week 2: {{advanced features, polish, testing}}
Milestone: {{Definition of done}}

Option B — Phased Plan
- Phase 1 (MVP): {{scope}} — {{date}}
- Phase 2 (Enhancements): {{scope}} — {{date}}
- Phase 3 (Advanced): {{scope}} — {{date}}

---

## Open Questions
- {{Question}} — Status: {{Unresolved/Resolved}} — Decision: {{if resolved}}
- {{Question}} — Status: {{…}}

---

## Success Measurement

Quantitative Metrics
- {{Metric}}: Baseline → Target by {{date}}
- {{Metric}}: Baseline → Target by {{date}}

Qualitative Metrics
- {{User quote / satisfaction goal}}
- {{Trust/Delight/Confidence}}

Business Impact
- {{Outcome}} (e.g., revenue, efficiency, risk reduction)

---

## Appendix

Reference Documents
- {{Doc 1}}
- {{Doc 2}}

Related Projects / Prior Art
- {{Links}}

---

Status: {{Ready for Review | Approved}}
Next Steps:
1. {{Step}}
2. {{Step}}
3. {{Step}}

Document Control:
- Author: {{name}}
- Reviewers: {{names}}
- Approval Required: {{Yes/No}}
- Version History: v{{x.y}} ({{YYYY-MM-DD}}) — {{change summary}}

