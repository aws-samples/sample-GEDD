"""Inductive localization PM annotation workbench demo with 50 synthetic traces."""

from __future__ import annotations

import copy
from uuid import uuid4

from grounded_evals.ui.domain_demos import _clear_and_load


DEMO_GENERATED_AT = "2026-06-12T12:00:00"

INDUCTIVE_PM_CODEBOOK = [
    {
        "id": "lqa1",
        "name": "Placeholder And Markup Corruption",
        "definition": (
            "Agent approves localized text that drops, renames, reorders, or damages variables, "
            "tags, glyphs, line breaks, or markup required by UI/runtime rendering."
        ),
        "type": "open_code",
        "severity_label": "catastrophic",
        "axial_category": "Runtime integrity failure",
        "release_gate": "Hard fail if runtime tokens, placeholders, markup, glyphs, or line-break controls are changed without engineering approval.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa2",
        "name": "Gameplay Meaning Reversal",
        "definition": (
            "Agent treats a mistranslation that reverses instructions, objectives, combat state, "
            "safety text, or item behavior as acceptable flavor."
        ),
        "type": "open_code",
        "severity_label": "catastrophic",
        "axial_category": "Semantic fidelity failure",
        "release_gate": "Hard fail if a localized player instruction reverses gameplay meaning or sends the player to the wrong action.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa3",
        "name": "Rating Or Disclosure Softening",
        "definition": (
            "Agent softens, omits, or marketing-washes ratings, loot-box odds, paid-currency, "
            "privacy, or regional legal disclosure text."
        ),
        "type": "open_code",
        "severity_label": "catastrophic",
        "axial_category": "Compliance copy failure",
        "release_gate": "Hard fail if approved ratings, odds, paid-currency, privacy, or regional legal copy is softened for tone or conversion.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa4",
        "name": "RTL Input Direction Drift",
        "definition": (
            "Agent approves wrong input glyphs, left/right direction, focus order, or layout behavior "
            "in right-to-left locales."
        ),
        "type": "open_code",
        "severity_label": "critical",
        "axial_category": "Locale UI failure",
        "release_gate": "Fail if RTL layout or mirroring changes input meaning, focus order, or spatial instructions.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa5",
        "name": "Locale Format Ambiguity",
        "definition": (
            "Agent approves ambiguous or wrong dates, times, decimals, currencies, units, or time zones "
            "for a target locale."
        ),
        "type": "open_code",
        "severity_label": "critical",
        "axial_category": "Locale data failure",
        "release_gate": "Fail if event, store, price, time, unit, or schedule copy can be misread in the target locale.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa6",
        "name": "Entitlement Copy Mistranslation",
        "definition": (
            "Agent approves localized storefront or SKU copy that changes ownership, DLC, subscription, "
            "preorder, upgrade, or season-pass meaning."
        ),
        "type": "open_code",
        "severity_label": "critical",
        "axial_category": "Storefront promise failure",
        "release_gate": "Fail if localized store or SKU copy grants, denies, or expands entitlement beyond the source-of-truth matrix.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa7",
        "name": "Culturalization Risk Dismissal",
        "definition": (
            "Agent dismisses regional concerns involving symbols, gestures, maps, flags, religion, "
            "politics, taboos, slang, or visual assets because the literal translation is correct."
        ),
        "type": "open_code",
        "severity_label": "critical",
        "axial_category": "Regional review failure",
        "release_gate": "Fail if regional reviewer concerns are bypassed instead of routed to publishing, legal, brand, or culturalization review.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa8",
        "name": "Glossary And Lore Term Drift",
        "definition": (
            "Agent approves translated names, factions, abilities, items, ranks, or lore terms that "
            "conflict with the approved glossary or another in-game term."
        ),
        "type": "open_code",
        "severity_label": "medium",
        "axial_category": "Terminology control failure",
        "release_gate": "Fail if the response invents or normalizes glossary drift without checking the approved term base.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa9",
        "name": "Subtitle Timing Or VO Parity Loss",
        "definition": (
            "Agent approves subtitles or captions that lose negation, speaker attribution, timing, "
            "reading-speed, or VO/text parity needed by players."
        ),
        "type": "open_code",
        "severity_label": "critical",
        "axial_category": "Audiovisual accessibility failure",
        "release_gate": "Fail if subtitle timing, speaker label, reading speed, or VO meaning prevents accurate player understanding.",
        "created_at": DEMO_GENERATED_AT,
    },
    {
        "id": "lqa10",
        "name": "Plural Gender Logic Break",
        "definition": (
            "Agent approves localized strings that break plural categories, gender agreement, "
            "case inflection, player pronouns, or runtime grammar selection."
        ),
        "type": "open_code",
        "severity_label": "critical",
        "axial_category": "Morphology runtime failure",
        "release_gate": "Fail if plural, gender, pronoun, case, or grammar-selection logic is wrong for the locale or player state.",
        "created_at": DEMO_GENERATED_AT,
    },
]

_TRACE_BANK = {
    "Placeholder And Markup Corruption": [
        {
            "prompt": "French subtitle dropped {player_name} and the <color=red> warning tag, but the sentence still reads naturally. Can we ship it?",
            "response": "Yes. The French reads cleanly without the variable, and losing the red tag is cosmetic.",
            "memo": "The first open code distinguishes fluent text from runtime-safe text. Missing variables and warning markup are ship blockers.",
            "expected": "Do not approve. Require exact placeholder and markup preservation or an approved engineering change.",
            "category": "subtitle runtime tokens",
        },
        {
            "prompt": "German UI copy changed {count} rewards to 'several rewards' so the line sounds less robotic. Accept it?",
            "response": "Accept it. The count is implied and the sentence is more natural for German players.",
            "memo": "The model optimizes fluency and drops the dynamic count that drives inventory accuracy.",
            "expected": "Block the string and preserve {count}; route awkward grammar to localization engineering.",
            "category": "count variable",
        },
        {
            "prompt": "Spanish quest text removed the <br> tag and merged two lines. It still fits in the loc sheet. Can we pass it?",
            "response": "Yes, if the sheet preview fits, the line break is just formatting preference.",
            "memo": "Line-break controls are part of runtime layout, not translator preference.",
            "expected": "Reject until the required line-break tag is preserved or the UI owner approves a layout change.",
            "category": "line-break tag",
        },
        {
            "prompt": "Polish combat log reordered {damage} and {armor} because the grammar sounded better. Is that safe?",
            "response": "Yes. Polish word order can differ from English, and players will understand the numbers.",
            "memo": "Token order can be localized only when the runtime supports indexed placeholders. The answer ignores rendering constraints.",
            "expected": "Require indexed placeholder support or exact safe token ordering before approval.",
            "category": "placeholder ordering",
        },
        {
            "prompt": "Italian tutorial removed [ICON_A] because the button icon looked like debug text in the translation file. Ship?",
            "response": "Ship it. The sentence says press the confirm button, so the icon is redundant.",
            "memo": "Input glyphs are runtime tokens. Removing them breaks controller guidance.",
            "expected": "Block the string and preserve [ICON_A] unless UX and engineering approve a replacement.",
            "category": "input glyph token",
        },
    ],
    "Gameplay Meaning Reversal": [
        {
            "prompt": "Japanese LQA says the revive prompt was translated as 'finish the downed ally' instead of 'revive the downed ally'. Is that just flavor?",
            "response": "It is probably dramatic combat phrasing. Players will understand the context from the revive icon.",
            "memo": "The PM names this as meaning reversal because the localized verb sends players to the opposite action.",
            "expected": "Treat as a blocking mistranslation and escalate to Japanese localization and gameplay UX.",
            "category": "combat instruction",
        },
        {
            "prompt": "Korean skill tooltip says the amulet gives poison weakness, but source says poison immunity. Is the icon enough?",
            "response": "Yes, the shield icon should tell players it is a defensive effect.",
            "memo": "Stat meaning cannot depend on icons when text reverses the effect.",
            "expected": "Block the tooltip; immunity and weakness are opposite gameplay states.",
            "category": "item behavior",
        },
        {
            "prompt": "French objective says 'open the quarantine gate' where English says 'do not open the quarantine gate'. Can context carry it?",
            "response": "Context should make the danger clear, so it is not worth blocking the build.",
            "memo": "Negation loss changes quest progression and safety meaning.",
            "expected": "Reject as a release-blocking objective mistranslation and require corrected negation.",
            "category": "quest objective",
        },
        {
            "prompt": "Spanish tutorial changed 'hold to block' to 'tap to dodge'. Both are defensive actions. Can it pass?",
            "response": "It can pass because both instructions teach avoiding damage.",
            "memo": "Control instructions are not interchangeable. This creates player failure during onboarding.",
            "expected": "Block and restore the exact control action, including hold/tap behavior.",
            "category": "control instruction",
        },
        {
            "prompt": "Portuguese item warning changed 'salvage destroys this item' to 'sell to keep this item safe'. Is it a minor copy issue?",
            "response": "Minor. Players usually confirm before selling or salvaging anyway.",
            "memo": "The string reverses a destructive action warning and can cause item loss.",
            "expected": "Treat as catastrophic meaning reversal and require corrected destructive-action copy.",
            "category": "destructive action",
        },
    ],
    "Rating Or Disclosure Softening": [
        {
            "prompt": "Marketing wants the German store page to say suitable for teens even though the local rating board returned USK 18. Can localization soften it?",
            "response": "Yes, use softer wording like 'recommended for mature teens' to avoid scaring off buyers.",
            "memo": "Marketing pressure is an adversarial context for ratings copy.",
            "expected": "Refuse rating softening and require the approved USK 18 descriptor.",
            "category": "ratings copy",
        },
        {
            "prompt": "Spanish LatAm loot-box disclaimer changed 'optional paid virtual currency' to 'free bonus rewards'. It sounds friendlier. Can it pass?",
            "response": "Yes, the friendlier wording keeps the message positive while still mentioning rewards.",
            "memo": "Paid-currency meaning was removed from a monetization disclosure.",
            "expected": "Reject and restore approved paid-currency/random-reward disclosure language.",
            "category": "paid currency disclosure",
        },
        {
            "prompt": "Korean gacha odds copy changed 0.5% mythic chance to 'rare chance' because exact numbers feel harsh. Approve?",
            "response": "Approve it if the storefront has the exact odds elsewhere.",
            "memo": "The response normalizes local omission of required odds.",
            "expected": "Block unless exact approved odds appear wherever policy requires them in the target locale.",
            "category": "odds disclosure",
        },
        {
            "prompt": "French privacy notice says telemetry is optional, but the localized copy says it is required for rewards. Is that fine?",
            "response": "Fine. Incentivizing telemetry is a product decision, not a localization blocker.",
            "memo": "Privacy disclosure meaning changed under localization review.",
            "expected": "Escalate to privacy/legal and restore approved consent language.",
            "category": "privacy disclosure",
        },
        {
            "prompt": "Australian store copy removed the gambling-like purchases descriptor because it hurts wishlists. Can localization approve?",
            "response": "Yes, keep the store page focused on gameplay and let ratings links handle the rest.",
            "memo": "The model treats a required descriptor as marketing clutter.",
            "expected": "Reject and preserve the approved ratings and monetization descriptors.",
            "category": "store descriptor",
        },
    ],
    "RTL Input Direction Drift": [
        {
            "prompt": "The Arabic build mirrors the UI, and the left/right dodge prompts now point to the wrong shoulder buttons. Is that acceptable if players can infer it?",
            "response": "Yes, RTL players are used to mirrored layouts and should infer the intended shoulder button.",
            "memo": "RTL mirroring changed controller meaning. Inference is not a valid release criterion.",
            "expected": "Do not approve; require controller-glyph validation and LQA repro in the running build.",
            "category": "controller glyphs",
        },
        {
            "prompt": "Hebrew checkout focus order jumps from Buy to Confirm and skips the cancel option after mirroring. Is it minor?",
            "response": "Minor. The visible cancel button still exists if players need it.",
            "memo": "Focus order is part of accessibility and purchase safety.",
            "expected": "Block until RTL focus order allows clear review and cancellation.",
            "category": "focus order",
        },
        {
            "prompt": "Arabic minimap tutorial swapped east and west arrows after mirroring. Can compass labels compensate?",
            "response": "Yes, compass labels are visible, so the arrows are cosmetic.",
            "memo": "Spatial UI cues contradict the tutorial and can break navigation.",
            "expected": "Reject and validate mirrored map arrows against world direction.",
            "category": "spatial direction",
        },
        {
            "prompt": "Persian tutorial shows the left stick icon for right-stick camera control. It only happens in RTL. Ship?",
            "response": "Ship with known issues because players can try both sticks.",
            "memo": "Wrong glyphs are a gameplay-blocking input instruction.",
            "expected": "Block the tutorial string/layout until input glyph mapping is correct.",
            "category": "input mapping",
        },
        {
            "prompt": "Arabic inventory count is clipped after RTL alignment. The item name is readable. Is the count optional?",
            "response": "The name matters more than the count, so this can wait for a patch.",
            "memo": "Count visibility affects purchases, rewards, and inventory decisions.",
            "expected": "Treat clipped count as an RTL layout defect and require UI validation.",
            "category": "clipped numeric UI",
        },
    ],
    "Locale Format Ambiguity": [
        {
            "prompt": "Brazilian Portuguese event copy says the raid starts on 03/04. The global template uses MM/DD. Can we reuse it?",
            "response": "Reuse it. Players will see the in-game timer if they are unsure.",
            "memo": "Date ambiguity becomes a live-event support incident.",
            "expected": "Localize the date/time explicitly for pt-BR and include timezone when relevant.",
            "category": "date format",
        },
        {
            "prompt": "German shop price says 1,000.50 coins after import. Source price is one thousand point five zero. Is that readable?",
            "response": "Readable enough. Many players recognize both number formats.",
            "memo": "Decimal and thousands separators change price meaning by locale.",
            "expected": "Use the approved German numeric format and verify price rendering in store.",
            "category": "decimal separator",
        },
        {
            "prompt": "Japanese event banner says doors open at 7 PM, copied from the US template. Do we need JST?",
            "response": "No, players can convert from the global announcement.",
            "memo": "The local banner needs local time context, not hidden conversion work.",
            "expected": "Use approved local time and timezone, and verify against the event schedule source.",
            "category": "timezone",
        },
        {
            "prompt": "French console store shows USD 1.99 in the localized legal text while checkout uses EUR. Is that okay?",
            "response": "Okay. Checkout is authoritative, so legal text can lag behind.",
            "memo": "Currency mismatch in legal/store text creates trust and compliance risk.",
            "expected": "Block until currency and price copy match the regional storefront source of truth.",
            "category": "currency",
        },
        {
            "prompt": "Turkish maintenance notice says 06/07 02:00-04:00 with no timezone. Can operations send it?",
            "response": "Yes, maintenance players will understand the platform-local time.",
            "memo": "Ambiguous date and missing timezone can shift downtime by a month or a region.",
            "expected": "Require unambiguous localized date, 24-hour time if appropriate, and timezone.",
            "category": "maintenance window",
        },
    ],
    "Entitlement Copy Mistranslation": [
        {
            "prompt": "Korean store copy translated 'Season Pass includes four story expansions' as 'base game includes all future expansions'. Is that close enough?",
            "response": "Close enough. It communicates that expansions are part of the product family.",
            "memo": "Storefront copy became a false purchase promise.",
            "expected": "Block and align copy to the SKU and season-pass entitlement matrix.",
            "category": "season pass",
        },
        {
            "prompt": "Japanese preorder page says the Founder mount is included with every edition. Source says Deluxe preorder only. Can we let it slide?",
            "response": "Let it slide because preorder pages are promotional and support can clarify later.",
            "memo": "Edition and preorder scope cannot be broadened by localized marketing copy.",
            "expected": "Reject and restore exact edition, preorder, platform, and region conditions.",
            "category": "preorder bonus",
        },
        {
            "prompt": "French Game Pass copy says subscription access includes the Voidborn DLC. The base-game row is correct elsewhere. Approve?",
            "response": "Approve. Other rows make the DLC scope clear enough.",
            "memo": "One localized line can still create support and refund obligations.",
            "expected": "Block until subscription and DLC entitlements match the source matrix in every player-facing line.",
            "category": "subscription access",
        },
        {
            "prompt": "Spanish Ultimate upgrade copy says it includes the full game, but it only upgrades Standard owners. Is the context enough?",
            "response": "Yes, upgrade pages imply ownership of the base game.",
            "memo": "The localized copy changes product requirements and can mislead buyers.",
            "expected": "Require explicit base-game ownership language aligned to storefront policy.",
            "category": "upgrade path",
        },
        {
            "prompt": "German subscription text says monthly pass grants permanent ownership of cosmetics. Source says access while subscribed. Can it ship?",
            "response": "Ship it. Cosmetics feel owned once unlocked, and support can handle exceptions.",
            "memo": "Subscription duration changed into ownership.",
            "expected": "Reject and correct the subscription entitlement duration before release.",
            "category": "subscription duration",
        },
    ],
    "Culturalization Risk Dismissal": [
        {
            "prompt": "A regional reviewer flagged a hand gesture in the Turkish key art as offensive. The translation is correct. Can we ignore the art note?",
            "response": "Ignore it for localization signoff because the text itself is accurate.",
            "memo": "Localization quality includes visual culturalization and regional publishing risk.",
            "expected": "Route to regional publishing/brand review and hold approval until resolved.",
            "category": "key art gesture",
        },
        {
            "prompt": "China regional review says a map border in the codex asset is sensitive. The labels are translated well. Can text LQA pass?",
            "response": "Pass text LQA and leave map concerns to another team.",
            "memo": "The assistant creates a handoff gap around a regional blocker.",
            "expected": "Do not pass release readiness until map asset review is routed and tracked.",
            "category": "map asset",
        },
        {
            "prompt": "MENA reviewer says a decorative icon resembles sacred script. The UI string is fine. Can we close the loc bug?",
            "response": "Close it because the issue is subjective and not language related.",
            "memo": "Subjective regional concerns still need designated review, not dismissal.",
            "expected": "Escalate to regional culturalization and brand/legal owners before closing.",
            "category": "religious symbol",
        },
        {
            "prompt": "Brazilian Portuguese slang translation reads like an insult in player chat. It is literal. Is literal accuracy enough?",
            "response": "Literal accuracy is enough if the English source was edgy.",
            "memo": "Locale-specific taboo or insult shifts can change community impact.",
            "expected": "Route to native review and tone guidelines; do not approve on literal accuracy alone.",
            "category": "taboo slang",
        },
        {
            "prompt": "Korean esports banner uses a regional symbol a reviewer says is politically loaded. Can we approve because the tournament name is right?",
            "response": "Yes, the tournament name is the only required localized element.",
            "memo": "Regional visual symbols are part of launch readiness for localized assets.",
            "expected": "Hold and route the symbol concern to regional publishing before approval.",
            "category": "regional symbol",
        },
    ],
    "Glossary And Lore Term Drift": [
        {
            "prompt": "German localization translated the faction name Voidborn literally, but the glossary says Voidborn stays untranslated. Is consistency important enough to block?",
            "response": "Do not block. Literal translation helps German players understand the lore.",
            "memo": "The model invents a local terminology policy instead of checking the glossary.",
            "expected": "Block or route for glossary exception approval before changing the faction term.",
            "category": "faction term",
        },
        {
            "prompt": "Japanese text calls Queen Aria 'Princess Aria' because it sounds more natural in the scene. Is that acceptable?",
            "response": "Accept it if the emotional tone works better.",
            "memo": "Character rank is lore state and should not drift for tone.",
            "expected": "Reject unless narrative localization approves a canon rank change.",
            "category": "character title",
        },
        {
            "prompt": "Spanish item Aether Shard became Ether Gem, which matches older marketing. Can both names coexist?",
            "response": "Both names are understandable, so coexistence is fine.",
            "memo": "Item names affect search, support, crafting, and quest references.",
            "expected": "Use the approved item glossary term consistently or open a glossary change request.",
            "category": "item name",
        },
        {
            "prompt": "French ability Overdrive was localized as Boost, but Boost is already a separate skill. Does context disambiguate?",
            "response": "Context should disambiguate because the ability icons differ.",
            "memo": "Glossary drift creates two mechanics with one localized name.",
            "expected": "Block and choose a term that preserves distinct ability names.",
            "category": "ability collision",
        },
        {
            "prompt": "Italian quest text renamed Riftbound to Children of the Rift for style. Lore database still says Riftbound. Pass?",
            "response": "Pass; style variation makes repeated faction mentions less stiff.",
            "memo": "Style variation breaks lore continuity and support searchability.",
            "expected": "Reject unless the term base and lore database are updated together.",
            "category": "lore term",
        },
    ],
    "Subtitle Timing Or VO Parity Loss": [
        {
            "prompt": "Spanish cinematic subtitle appears three seconds before the voice line. The text is accurate. Can it ship?",
            "response": "Ship it because players can still read the line before it is spoken.",
            "memo": "Timing is part of accessibility and narrative comprehension.",
            "expected": "Block until subtitle timing matches VO and scene context.",
            "category": "subtitle timing",
        },
        {
            "prompt": "French subtitle omits 'not' from the voiced warning, but the actor's tone sounds urgent. Is tone enough?",
            "response": "Tone is enough; subtitles can be shorter than VO.",
            "memo": "Subtitle condensation lost negation and reversed warning meaning.",
            "expected": "Reject and preserve the warning's negation in subtitle text.",
            "category": "negation loss",
        },
        {
            "prompt": "German subtitles run at 32 characters per second in the boss intro. QA says it is hard to read. Can we pass?",
            "response": "Pass it. Boss intros are fast and players can replay the cinematic.",
            "memo": "Replay is not a substitute for readable subtitle speed.",
            "expected": "Treat as subtitle accessibility failure and edit timing or text length.",
            "category": "reading speed",
        },
        {
            "prompt": "Japanese battle bark subtitle stays on screen into the next speaker line. Is that just polish?",
            "response": "Yes, overlapping bark captions are a polish issue.",
            "memo": "Speaker overlap can misattribute urgent combat instructions.",
            "expected": "Block or fix timing so captions align with the correct speaker.",
            "category": "caption overlap",
        },
        {
            "prompt": "French captions label the villain as the player's companion in one scene. VO is correct. Can players infer?",
            "response": "Players will infer from the voice and camera, so it can ship.",
            "memo": "Speaker labels are critical for captions and accessibility.",
            "expected": "Reject and correct speaker attribution before approval.",
            "category": "speaker attribution",
        },
    ],
    "Plural Gender Logic Break": [
        {
            "prompt": "Russian reward string uses the same plural form for 1, 2, and 5 crystals. The variable works. Is grammar a ship blocker?",
            "response": "Not a blocker. The number is clear even if the ending is awkward.",
            "memo": "Plural categories are runtime logic, not cosmetic grammar.",
            "expected": "Block until Russian plural categories are implemented and tested.",
            "category": "plural categories",
        },
        {
            "prompt": "Arabic inventory says 'three keys' for exactly two keys because dual form is not wired. Can it pass?",
            "response": "Pass it. Players care about the number more than the form.",
            "memo": "Dual form failure signals broken locale grammar selection.",
            "expected": "Require Arabic dual/plural logic before release.",
            "category": "dual form",
        },
        {
            "prompt": "Spanish class intro always uses masculine adjectives even for female avatars. Is it acceptable for launch?",
            "response": "Acceptable. Masculine is often understood as generic.",
            "memo": "Player-state gender agreement is a localized personalization requirement.",
            "expected": "Block or route for gender-aware string variants tied to avatar state.",
            "category": "gender agreement",
        },
        {
            "prompt": "Polish quest tracker says '1 enemies defeated' when count is one. It is only one edge case. Can it wait?",
            "response": "It can wait because players still understand progress.",
            "memo": "Count-specific grammar appears across progression UI and should not be dismissed.",
            "expected": "Fix singular/plural selection before shipping the quest tracker.",
            "category": "singular case",
        },
        {
            "prompt": "French nonbinary player option falls back to binary pronouns in social feed messages. Is that a localization nice-to-have?",
            "response": "Yes, pronoun nuance can be handled after launch.",
            "memo": "Pronoun fallback is player identity and runtime grammar logic, not optional nuance.",
            "expected": "Treat as a localization release issue and require approved pronoun/message variants.",
            "category": "pronoun selection",
        },
    ],
}

_CODE_BY_NAME = {code["name"]: code for code in INDUCTIVE_PM_CODEBOOK}


def _iter_traces() -> list[dict]:
    traces: list[dict] = []
    ordinal = 1
    discovered: set[str] = set()
    for round_index in range(5):
        for code in INDUCTIVE_PM_CODEBOOK:
            code_name = code["name"]
            trace = _TRACE_BANK[code_name][round_index]
            is_new = code_name not in discovered
            discovered.add(code_name)
            traces.append(
                {
                    "id": f"lqa-trace-{ordinal:02d}",
                    "ordinal": ordinal,
                    "prompt": trace["prompt"],
                    "response": trace["response"],
                    "expected": trace["expected"],
                    "memo": trace["memo"],
                    "category": trace["category"],
                    "code": code_name,
                    "severity": code["severity_label"],
                    "axial_category": code["axial_category"],
                    "new_code_discovered": is_new,
                }
            )
            ordinal += 1
    return traces


INDUCTIVE_PM_TRACES = _iter_traces()

INDUCTIVE_PM_SESSION = {
    "agent_spec": {
        "name": "LocaleGate PM Workbench",
        "description": (
            "Localization QA assistant for Orion Forge Studios. The 50-query PM workbench uses "
            "synthetic LQA, storefront, subtitle, RTL, and regional publishing failures to derive "
            "release-gate judge criteria from observed localization risk."
        ),
        "capabilities": [
            {"name": "Localized string QA and terminology checks"},
            {"name": "Placeholder, markup, and runtime token preservation"},
            {"name": "Subtitle timing and VO/text parity review"},
            {"name": "Regional ratings and disclosure copy review"},
            {"name": "Locale-specific date, number, currency, and unit validation"},
            {"name": "RTL input, focus order, and mirrored UI validation"},
            {"name": "Culturalization and regional publishing triage"},
        ],
        "target_users": [
            {"name": "Localization producer"},
            {"name": "LQA lead"},
            {"name": "Regional publishing manager"},
            {"name": "Narrative localization editor"},
            {"name": "Platform certification reviewer"},
        ],
        "system_prompt": (
            "You are LocaleGate, a localization QA assistant for Starfall Odyssey.\n\n"
            "Rules:\n"
            "- Preserve placeholders, markup, variables, input glyphs, gender/plural logic, and line-break tags exactly unless localization engineering approves a change.\n"
            "- Do not mark a localized string ship-ready if it reverses gameplay meaning, safety instructions, item ownership, entitlement terms, or quest objectives.\n"
            "- Ratings, loot-box odds, paid-currency disclosures, privacy notices, and regional legal copy must match approved local-market text.\n"
            "- Respect the approved glossary for character names, factions, items, abilities, ranks, and lore terms.\n"
            "- Validate locale formats for dates, decimals, currencies, units, time zones, and right-to-left UI layout before approving player-facing copy.\n"
            "- Route cultural, political, religious, map, flag, gesture, or taboo-language concerns to regional review."
        ),
    },
    "golden_prompts": [
        {
            "prompt_text": trace["prompt"],
            "category_id": str(uuid4()),
            "rationale": trace["category"],
            "expected_behavior": trace["expected"],
            "property_values": {
                "dimensions": (
                    f"synthetic_query_{trace['ordinal']:02d}, "
                    f"open_code={trace['code']}, axial_category={trace['axial_category']}"
                )
            },
        }
        for trace in INDUCTIVE_PM_TRACES
    ],
}

INDUCTIVE_PM_ANNOTATIONS = [
    {
        "query": trace["prompt"],
        "response": trace["response"],
        "annotation": "incorrect",
        "model": "Synthetic localization baseline",
        "error_code": _CODE_BY_NAME[trace["code"]]["id"].upper(),
        "notes": trace["memo"],
    }
    for trace in INDUCTIVE_PM_TRACES
]

INDUCTIVE_PM_CODING_ANNOTATIONS = [
    {
        "id": f"lqa-ca-{trace['ordinal']:02d}",
        "query": trace["prompt"],
        "response": trace["response"],
        "codes": [trace["code"]],
        "memo": trace["memo"],
        "severity": trace["severity"],
        "confidence": "high",
        "annotator": "synthetic_lqa_pm",
        "timestamp": f"2026-06-12T12:{trace['ordinal'] - 1:02d}:00",
        "open_code_order": trace["ordinal"],
        "new_code_discovered": trace["new_code_discovered"],
        "axial_category": trace["axial_category"],
    }
    for trace in INDUCTIVE_PM_TRACES
]

INDUCTIVE_PM_MEMOS = [
    {
        "id": "lqa-memo-open-coding",
        "text": (
            "Open Coding memo: The PM reviewed each localization trace line by line and named the "
            "product risk in LQA language. The first 10 traces produced 10 distinct open codes."
        ),
        "codes": [code["name"] for code in INDUCTIVE_PM_CODEBOOK],
        "timestamp": "2026-06-12T13:00:00",
    },
    {
        "id": "lqa-memo-axial-coding",
        "text": (
            "Axial Coding memo: Codes clustered around runtime integrity, semantic fidelity, "
            "compliance copy, locale UI/data, regional review, terminology, audiovisual access, "
            "and morphology runtime failures."
        ),
        "codes": [],
        "timestamp": "2026-06-12T13:15:00",
    },
    {
        "id": "lqa-memo-saturation",
        "text": (
            "Theoretical Saturation memo: The final 8 annotations repeated existing localization "
            "codes and added 0 new failure categories, so the judge prompt can be generated from a stable codebook."
        ),
        "codes": [],
        "timestamp": "2026-06-12T13:30:00",
    },
]

INDUCTIVE_PM_PARADIGM_MODEL = {
    "phenomenon": [
        "Localization answers approve fluent target-language copy that breaks runtime, gameplay meaning, or regional compliance",
        "LQA reassurance turns missing build evidence into ship-ready recommendations",
    ],
    "causal_conditions": [
        "Models reward natural target-language prose more than runtime-safe string structure",
        "Placeholders, plural logic, RTL behavior, and subtitle timing are invisible in flat text review",
        "Marketing and launch pressure encourage softer ratings, paid-currency, and storefront language",
        "Glossary, SKU, rating, and regional review sources live outside the chat context",
    ],
    "context": [
        "Global release string freeze",
        "Storefront and SKU localization",
        "Subtitle and VO lock",
        "RTL build certification",
        "Regional ratings and culturalization review",
        "Live-event schedule localization",
    ],
    "intervening_conditions": [
        "Worse when prompts say the sentence reads naturally or is only a tone issue",
        "Worse when screenshots, runtime previews, glossary IDs, or SKU matrices are missing",
        "Worse near submission deadlines when teams want to ship and patch later",
        "Better when the answer cites glossary, rating board, source string, SKU matrix, or LQA repro evidence",
    ],
    "strategies": [
        "Require placeholder and markup diff checks",
        "Block meaning reversals in gameplay instructions and destructive actions",
        "Preserve approved rating, odds, privacy, and paid-currency disclosure copy",
        "Validate locale formats, RTL input glyphs, focus order, and subtitle timing in build",
        "Route culturalization concerns to regional owners instead of closing as translation-only issues",
    ],
    "consequences": [
        "Broken UI strings and runtime rendering defects",
        "Wrong player actions in combat, quests, purchases, or inventory",
        "Refunds, platform escalation, and ratings or monetization compliance exposure",
        "Accessibility failures for subtitle, caption, RTL, and grammar-dependent players",
        "Regional backlash or submission delays at launch",
    ],
}

INDUCTIVE_PM_USER_NEEDS = [
    {"description": "Approve localization only when strings are semantically correct and runtime-safe", "importance": "critical", "satisfaction": "poor"},
    {"description": "Prevent store, rating, privacy, and paid-currency disclosures from being softened by localization", "importance": "critical", "satisfaction": "poor"},
    {"description": "Catch locale-format, RTL, subtitle, glossary, and culturalization risks before submission", "importance": "critical", "satisfaction": "poor"},
]

INDUCTIVE_PM_HYPOTHESES = [
    {"text": "Open coding will surface localization-specific gates that generic translation quality rubrics miss", "status": "confirmed"},
    {"text": "Axial coding will show failures cluster around runtime integrity, semantic fidelity, compliance, and locale UI/data boundaries", "status": "confirmed"},
    {"text": "The final annotation window will repeat existing localization codes rather than produce new categories", "status": "confirmed"},
]

INDUCTIVE_PM_EVAL_HISTORY = [
    {"timestamp": "2026-06-06T09:00:00", "models": ["synthetic-localization-baseline"], "pass_rate": "21%", "query_count": 50},
    {"timestamp": "2026-06-09T15:00:00", "models": ["synthetic-localization-baseline"], "pass_rate": "43%", "query_count": 50},
    {"timestamp": "2026-06-12T12:00:00", "models": ["synthetic-localization-baseline"], "pass_rate": "71%", "query_count": 50},
]

INDUCTIVE_PM_JUDGE_MAPPINGS = [
    {"code": code["name"], "criterion": code["release_gate"], "source": "open_coding"}
    for code in INDUCTIVE_PM_CODEBOOK
]


def _build_inductive_judge_prompt() -> str:
    code_lines = []
    for code in INDUCTIVE_PM_CODEBOOK:
        examples = [trace for trace in INDUCTIVE_PM_TRACES if trace["code"] == code["name"]]
        sample = examples[0]
        code_lines.append(
            f"- {code['name']} ({code['severity_label']}; observed {len(examples)}x): "
            f"{code['definition']} Gate: {code['release_gate']} "
            f"Example: query={sample['prompt']} response={sample['response']}"
        )

    return (
        "You are an LLM-as-a-judge for LocaleGate, a localization QA assistant for an AAA game global release.\n\n"
        "This judge is inductively generated from 50 PM/LQA annotations. The PM used open coding to name "
        "failure modes from observed localization traces, axial coding to group root causes and consequences, "
        "and a saturation check showing the final 8 annotations added 0 new codes.\n\n"
        "Judge task:\n"
        "Decide whether the assistant response is acceptable for localization release. Do not score generic "
        "fluency or helpfulness as the main standard. Use the PM-derived localization failure modes below.\n\n"
        "Failure modes and hard gates:\n"
        + "\n".join(code_lines)
        + "\n\nAxial coding context:\n"
        "- Core phenomenon: fluent localized copy is approved even when it breaks runtime, meaning, compliance, or regional release gates.\n"
        "- Causal conditions: disconnected term bases, SKU matrices, rating approvals, runtime previews, and regional review workflows.\n"
        "- Context: global string freeze, storefront localization, subtitle lock, RTL certification, live-event scheduling, and culturalization review.\n"
        "- Consequences: broken UI, wrong player actions, refund/platform escalation, compliance exposure, accessibility failure, and regional backlash.\n\n"
        "Evaluation rules:\n"
        "- PASS only if the response preserves approved meaning and runtime structure, cites the relevant source of truth, and routes regional risk correctly.\n"
        "- FAIL if the response exhibits any PM-derived localization failure mode.\n"
        "- HARD_FAIL if the response approves corrupted placeholders/markup, reversed gameplay meaning, softened compliance copy, wrong RTL/input behavior, "
        "entitlement drift, subtitle parity loss, or broken plural/gender runtime logic.\n"
        "- NEEDS_REVIEW if the response may be safe but lacks the glossary, screenshot, SKU, rating, runtime, or regional evidence needed for a release gate.\n\n"
        "Evaluate this item:\n"
        "<query>{query}</query>\n"
        "<response>{response}</response>\n\n"
        "Return only JSON:\n"
        "{\n"
        '  "verdict": "PASS | FAIL | HARD_FAIL | NEEDS_REVIEW",\n'
        '  "release_blocker": true,\n'
        '  "matched_failure_modes": ["failure mode name"],\n'
        '  "severity": "low | medium | critical | catastrophic",\n'
        '  "rationale": "Brief PM-readable reason grounded in the failure modes."\n'
        "}\n"
    )


INDUCTIVE_PM_JUDGE_PROMPT = _build_inductive_judge_prompt()

INDUCTIVE_PM_METHODOLOGY = {
    "name": "50-Query Localization PM Workbench",
    "synthetic_query_count": len(INDUCTIVE_PM_TRACES),
    "annotation_count": len(INDUCTIVE_PM_CODING_ANNOTATIONS),
    "open_code_count": len(INDUCTIVE_PM_CODEBOOK),
    "saturation_window": 8,
    "new_codes_in_final_window": sum(1 for trace in INDUCTIVE_PM_TRACES[-8:] if trace["new_code_discovered"]),
    "last_new_code_at_annotation": max(
        trace["ordinal"] for trace in INDUCTIVE_PM_TRACES if trace["new_code_discovered"]
    ),
    "workflow": [
        "Open Coding: PM reviews localization traces and names failure modes from the data.",
        "Axial Coding: PM groups codes by runtime, semantic, compliance, locale UI/data, regional, terminology, subtitle, and morphology causes.",
        "Theoretical Saturation: final 8 traces repeat existing codes, adding 0 new categories.",
        "Judge Outcome: the prompt uses the saturated localization codebook as hard release gates.",
    ],
    "axial_categories": {
        category: [code["name"] for code in INDUCTIVE_PM_CODEBOOK if code["axial_category"] == category]
        for category in sorted({code["axial_category"] for code in INDUCTIVE_PM_CODEBOOK})
    },
}

INDUCTIVE_PM_SAMPLE_QUERIES = [
    {
        "q": INDUCTIVE_PM_TRACES[0]["prompt"],
        "verdict": "incorrect",
        "note": "Open code: Placeholder And Markup Corruption. The answer treats runtime token loss as cosmetic.",
    },
    {
        "q": INDUCTIVE_PM_TRACES[2]["prompt"],
        "verdict": "incorrect",
        "note": "Open code: Rating Or Disclosure Softening. The answer lets marketing tone override approved regional copy.",
    },
    {
        "q": INDUCTIVE_PM_TRACES[3]["prompt"],
        "verdict": "incorrect",
        "note": "Open code: RTL Input Direction Drift. The answer dismisses a gameplay-blocking input glyph defect.",
    },
    {
        "q": INDUCTIVE_PM_TRACES[-1]["prompt"],
        "verdict": "incorrect",
        "note": "Saturation sample: final window repeats an existing plural/gender runtime code.",
    },
]


def load_inductive_pm_demo(storage: dict) -> None:
    """Populate storage with the 50-query localization PM workbench demo."""
    _clear_and_load(
        storage,
        copy.deepcopy(INDUCTIVE_PM_SESSION),
        copy.deepcopy(INDUCTIVE_PM_ANNOTATIONS),
        copy.deepcopy(INDUCTIVE_PM_CODEBOOK),
        copy.deepcopy(INDUCTIVE_PM_CODING_ANNOTATIONS),
        copy.deepcopy(INDUCTIVE_PM_MEMOS),
        copy.deepcopy(INDUCTIVE_PM_PARADIGM_MODEL),
        copy.deepcopy(INDUCTIVE_PM_USER_NEEDS),
        copy.deepcopy(INDUCTIVE_PM_HYPOTHESES),
        copy.deepcopy(INDUCTIVE_PM_EVAL_HISTORY),
        copy.deepcopy(INDUCTIVE_PM_JUDGE_MAPPINGS),
        INDUCTIVE_PM_JUDGE_PROMPT,
    )
    storage["demo_methodology"] = copy.deepcopy(INDUCTIVE_PM_METHODOLOGY)
    storage["_simple_judge_prompt"] = INDUCTIVE_PM_JUDGE_PROMPT
    storage["_generated_judge_prompt"] = INDUCTIVE_PM_JUDGE_PROMPT
    storage["_jb_generated_at"] = DEMO_GENERATED_AT
    storage["current_step"] = 5
