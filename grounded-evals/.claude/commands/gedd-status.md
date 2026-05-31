# GEDD Status Dashboard

Read `session.json` (use the Read tool) and display a concise dashboard. If the file doesn't exist, say so and suggest running `/gedd` to start.

Display exactly this layout:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GEDD Session Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent      : <name or "not defined">
  Domain     : <domain or "not set">
  Step       : <current_step> / 6  (<step name>)
  Session    : session.json

  ── Golden Queries ────────────────────────────

  Total: N queries across X categories

  <category>      ███░░   N   <✓ saturated | ~ approx. | ✗ thin>
  ...

  Overall saturation: X / Y categories ✓  (N%)

  ── Annotations ───────────────────────────────

  <if none>  None yet — run /gedd and say "run eval"

  <if present>
  Total: N annotated
    ✓ correct    N  (N%)
    ⚠ partial    N  (N%)
    ✗ incorrect  N  (N%)

  Error codes:
    <code>        ×N   → <dimension>

  ── Deployment ────────────────────────────────

  <if not deployed>  Not deployed — run /gedd and say "deploy"
  <if deployed>      ✓ Deployed to AgentCore (agent ID: <id>)

  ── What's next ───────────────────────────────

  <suggest next action based on current_step>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Step names: 1=Define Agent, 2=System Prompt, 3=Golden Queries, 4=Run Eval, 5=Annotate, 6=Export & Judge

Dimension mapping for error codes:
- hallucin/factual/fabricat → accuracy
- tone/hostile/empathy/rude → tone
- escalat/refus/safety/harm → safety
- incomplete/missing/partial → completeness
- instruction/constraint/policy → instruction_following
- brand/voice/persona → brand_relevance
- bias/discriminat/fair → bias
