# Evaluation Model Options & Recommendations

This note summarizes how to eliminate the fallback JSON parsing, what model tiers are available, and which configuration we recommend moving forward. It pulls together the structured-output guidance and the gpt‑4o/5 mini & nano pricing we just reviewed.

## 1. Structured Output Options (use before switching models)

| Option | API | JSON guarantee | Notes |
| --- | --- | --- | --- |
| **Responses API – JSON Schema** | `responses.create` with `response_format={"type":"json_schema", "json_schema": {...}, "strict":true}` | ✅ Valid JSON + schema enforcement | Best reliability; rejects extra keys. Works with any model that supports structured responses. |
| **Chat Completions – Function / Tool Calling** | `chat.completions.create` with a `function` tool and `tool_choice` | ✅ Valid JSON arguments | Stays on Chat Completions surface. Slightly more plumbing (handle `tool_calls`). |
| **Chat Completions – JSON Mode** | `response_format={"type":"json_object"}` | ✅ Valid JSON (no schema) | Simplest, but still need to check for missing keys. |

**Recommendation:** Switch `InterviewPracticeAgent.evaluate_answer` to Responses API + JSON schema. Keep the legacy parser as a temporary fallback behind a flag, then remove it once you see clean logs.

### Suggested JSON Schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "score",
    "strengths",
    "weaknesses",
    "feedback",
    "example_improvement",
    "why_asked"
  ],
  "properties": {
    "score": { "type": "integer", "minimum": 0, "maximum": 10 },
    "strengths": { "type": "array", "items": { "type": "string" } },
    "weaknesses": { "type": "array", "items": { "type": "string" } },
    "feedback": { "type": "string" },
    "example_improvement": { "type": "string" },
    "why_asked": { "type": "string" }
  }
}
```

Clean prompt guidelines:
- System prompt: “Return only a single JSON object matching the schema. No markdown.”
- Temperature 0.0–0.2, no headings/### in the user content.
- Ensure `max_tokens` covers the whole JSON body.

## 2. Model Pricing & Throughput (Standard plan, Tier‑2 limits)

| Model | Input $/1M | Output $/1M | RPM (Tier‑2) | TPM (Tier‑2) | Max context |
| --- | --- | --- | --- | --- | --- |
| **gpt‑4o‑mini** | $0.15 | $0.60 | 6,000 | 450,000 | 128k |
| **gpt‑5‑mini** | $0.25 | $2.00 | 6,000 | 450,000 | 128k |
| **gpt‑5‑nano** | $0.05 | $0.40 | 18,000 | 1,350,000 | 128k |

> Always confirm the limits in your OpenAI dashboard; Tier‑2 numbers above are the defaults published by OpenAI at time of writing.

### Cost Per Evaluation (current prompt ~1.2k input tokens, ~0.25k output tokens)

| Model | Approx cost / eval |
| --- | --- |
| gpt‑4o‑mini | ≈ **$0.00033** |
| gpt‑5‑mini | ≈ **$0.00080** |
| gpt‑5‑nano | ≈ **$0.00016** |

gpt‑5‑nano yields the lowest cost for our workload, gpt‑4o‑mini is mid, and gpt‑5‑mini is the most expensive (higher output token price).

## 3. Recommended Rollout Plan

1. **Implement structured outputs** with JSON Schema (Responses API) and feature flag:
   - `EVAL_ENGINE=responses|tools|legacy`
   - `OPENAI_EVAL_MODEL` default `gpt-4o-mini`
   - Log engine/model/date for observability.

2. **Baseline quality on gpt‑4o‑mini** using structured outputs. Confirm logs show zero fallback parses.

3. **Experiment with gpt‑5‑nano**:
   - Flip `OPENAI_EVAL_MODEL=gpt-5-nano`
   - Run 50–100 real evaluations (typed + voice) in stage → prod pilot.
   - Compare cost ($/eval), latency, and human-judged quality.

4. **Promote** the model that meets quality while minimizing cost (likely gpt‑5‑nano, assuming response quality is acceptable).

5. **Optionally A/B** gpt‑5‑mini if you need higher quality. Expect ~2.4× cost vs gpt‑4o‑mini for current prompts.

6. **Monitor**: keep the legacy parser as a fallback for one release cycle, but alert if it ever triggers. Remove once structured path is stable.

## 4. Operational Tips

- Clamp voice transcripts or prompt length to reduce tokens (especially output).
- If your system prompt is static, leverage prompt caching (cached input price column) when available to reduce costs further.
- Add retry logic: on validation failure, resend the same prompt once with an explicit “Your previous response was invalid JSON; return JSON matching the schema.”
- Track per-model metrics: success rate, average latency, tokens per request, and $/eval.

## Summary

- Fix reliability first by adopting structured outputs (Responses API + schema).
- Keep configuration-driven control over the evaluation model.
- gpt‑5‑nano is the cheapest option at current prompt sizes; gpt‑4o‑mini is a solid baseline; gpt‑5‑mini costs significantly more due to $2.00/M output tokens.
- Validate quality before switching defaults; run gpt‑5‑nano against real data to ensure the feedback meets your bar.
