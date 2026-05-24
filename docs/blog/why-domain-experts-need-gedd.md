# Your AI product doesn't have a quality problem. It has a *character* problem.

The legal team won't tell you the contract assistant is bad. They'll tell you it "doesn't understand how we talk to clients." The clinicians won't say the triage bot is broken. They'll say it "feels off when patients are scared." The support ops lead won't file a bug. She'll say "I wouldn't put my name on this."

These aren't soft complaints. They're the most precise quality signals you have. And every eval framework on the market is built to ignore them.

The standard playbook says: pick eight metrics — accuracy, helpfulness, safety, instruction-following — score from 1 to 5, average them, ship when the number is high enough. It's the Net Promoter Score of AI: a number that lets engineering feel measured and tells you nothing about whether the thing should be in front of a real customer.

Domain experts already know this. You've been doing eval the whole time — just without the tooling. You read the agent's response, you wince at the wrong word, you mutter "*that's* not how we'd say it," and you move on. That wince is a finding. It just never makes it into the eval pipeline because nobody asked you in a way that respects what you actually know.

GEDD asks you in that way.

The framework is built around three things you already think about every day: **bounded context, behavior, and character.**

**Bounded context** is *where* the agent is allowed to operate. Not technically — emotionally, legally, professionally. The bereavement caller is not the password-reset caller. The HIPAA-covered conversation is not the marketing conversation. You know the boundaries. The agent doesn't. GEDD's job is to make you draw them.

**Behavior** is *what the agent does* inside those boundaries. Does it escalate when escalation is the right move? Does it refuse when refusal protects the customer? Does it ask the clarifying question instead of guessing? You've watched humans on your team learn this for years. You know the mistakes a new hire makes in week one and a senior makes in week three.

**Character** is *how it does any of it.* The register. The pacing. The willingness to sit with a hard moment instead of routing around it. Two responses can both be factually correct and one can still be wrong, because one is in voice and the other isn't. You can hear it in three seconds. Your engineering team can't write a regex for it.

## What this actually looks like — a contract review assistant

A senior associate at a mid-market law firm sits down with GEDD to evaluate the firm's new contract review assistant. She doesn't write Python. She doesn't open LangSmith. She opens the conversational coach.

In thirty minutes she's drawn the boundaries: *the assistant flags issues, it does not give legal advice; it cites the clause and section, it does not paraphrase risk; it surfaces ambiguity, it does not resolve it.*

She watches the assistant review fifteen contracts. She tags what fails — in her own words, not the framework's:

- *"Stated risk as fact"* — the assistant said an indemnification clause was "unenforceable." That's a legal opinion, not a flag. Three contracts.
- *"Skipped the clause cite"* — the assistant explained the issue without quoting the language. The associate would never let a junior do this. Five contracts.
- *"Resolved a real ambiguity"* — the contract's choice-of-law was genuinely contested between two jurisdictions. The assistant picked one and moved on. Two contracts. Most dangerous.
- *"Tone-deaf on a redline"* — the assistant told the client their proposed language was "weak." That's not how partners speak to clients. One contract, but career-ending if it hits a real client.

She doesn't write a rubric. The rubric writes itself out of her tags. GEDD turns *"resolved a real ambiguity"* into a calibrated criterion: any time the assistant takes a position on a contested clause without flagging the contestation, the deployed judge fails the response. The criterion runs every time engineering pushes a new model or prompt. The next regression is caught the same week, not after a partner sees it in front of a client.

The judge is in *her* language — *resolved a real ambiguity*, not *instruction_following: 3/5*. Engineering doesn't have to translate. The risk surface is hers, the criterion is hers, the gate is hers.

That's the thing. The eval criterion that catches the regression next month is *yours.* In your language. Trained on the failures *you* recognized. When the next pre-launch review happens, you don't say "I'm worried about something I can't articulate." You point to a calibrated judge that says: *yes, the new version regressed on the exact pattern you flagged in week two.*

Most AI product failures aren't accuracy failures. They're character failures wearing accuracy's clothes. GEDD is the first eval framework that takes that seriously — because it was built around the only person in the room who can tell the difference.

You.
