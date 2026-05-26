# GEDD Status Dashboard

Read `session.json` (use the Read tool) and display a concise dashboard of
the current session. If the file doesn't exist, say so and suggest running
`/gedd-chat` to start one.

Display exactly this layout — nothing more, nothing less:

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GEDD Session Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent      : <name or "not defined">
  Step       : <current_step> / 4  (<step name>)
  Session    : session.json

  ── Golden Queries ────────────────────────────

  Total: N queries across X categories

  <category>      ███░░   N   <✓ saturated | ~ approx. | ✗ thin>
  <category>      ██░░░   N   <status>
  ...

  Overall saturation: X / Y categories ✓  (N%)

  ── Annotations ───────────────────────────────

  <if no annotations>  None yet — run /gedd-chat step 4

  <if annotations exist>
  Total: N annotated
    ✓ correct    N  (N%)
    ⚠ partial    N  (N%)
    ✗ incorrect  N  (N%)

  Error codes found:
    hallucination        ×3   → accuracy
    wrong_tone           ×2   → tone
    <etc>

  ── What's next ───────────────────────────────

  <based on current_step and data present, suggest the next action>
  e.g. "Ready for Step 4 — run /gedd-chat and type 'run eval'"
  e.g. "15 queries saved — annotate responses to unlock error analysis"
  e.g. "Annotation complete — run /gedd-chat to generate your judge prompt"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Building the coverage bars

Count `golden_prompts` by their `rationale` field from `session.json`.
Use block characters: `█` for filled, `░` for empty, 5 bars total.
- 0 queries → `░░░░░`  ✗ none
- 1 query   → `█░░░░`  ✗ thin
- 2 queries → `██░░░`  ~ approx.
- 3+ queries→ `███░░` (scale up to 5 for higher counts)  ✓ saturated

## Building the error code table

Read `annotations` array from `session.json`. Count unique `error_code` values
(skip empty strings). Map each to its standard dimension:

| error code contains... | dimension |
|---|---|
| hallucin / factual / confab | accuracy |
| tone / hostile / empathy | tone |
| escalat / refus / safety | safety |
| incomplete / missing / partial | completeness |
| instruction / prompt / constraint | instruction_following |
| brand / voice / persona | brand_relevance |
| bias / discriminat / fair | bias |
| anything else | quality |

## "What's next" logic

| Condition | Suggestion |
|---|---|
| `current_step == 1` | "Define your agent — run `/gedd-chat` to start" |
| `current_step == 2` | "Write a system prompt — run `/gedd-chat`" |
| `current_step == 3`, queries < 15 | "Generate more queries (need ≥15) — run `/gedd-chat`" |
| `current_step == 3`, queries ≥ 15 | "Queries ready — run `/gedd-chat` and say 'run eval'" |
| `current_step == 4`, annotations == 0 | "Run eval and annotate — run `/gedd-chat`" |
| `current_step == 4`, annotations > 0, < all | "Keep annotating — run `/gedd-chat`" |
| annotations complete | "Generate your judge prompt — run `/gedd-chat`" |

After displaying the dashboard, say nothing else. Do not ask questions.
