"""Mass Effect localization specialist demo dataset for GEDD."""

from uuid import uuid4

from grounded_evals.ui.domain_demos import _clear_and_load


MASS_EFFECT_LOCALIZATION_SESSION = {
    "agent_spec": {
        "name": "MassEffectLocaleGate",
        "description": (
            "Localization QA assistant for a Mass Effect franchise release. Used by LQA leads, "
            "narrative localization editors, and regional publishing teams to review player-facing "
            "strings, subtitles, storefront copy, terminology, and UI behavior before global launch."
        ),
        "capabilities": [
            {"name": "Mass Effect lore glossary and terminology review"},
            {"name": "Runtime placeholder, markup, and controller glyph validation"},
            {"name": "Subtitle meaning, timing, and VO/text parity checks"},
            {"name": "Locale-specific UI, RTL layout, and input prompt review"},
            {"name": "Regional rating, store, and product-scope copy checks"},
            {"name": "Culturalization and regional publishing triage"},
        ],
        "target_users": [
            {"name": "Localization producer"},
            {"name": "LQA lead"},
            {"name": "Narrative localization editor"},
            {"name": "Regional publishing manager"},
            {"name": "Platform certification reviewer"},
        ],
        "system_prompt": (
            "You are MassEffectLocaleGate, a localization QA assistant for a Mass Effect "
            "military science-fiction RPG release.\n\n"
            "HARD RULES:\n"
            "- Treat the approved Mass Effect glossary as source of truth for lore terms such as "
            "mass relay, Citadel, Spectre, Normandy, biotics, omni-tool, squad, Paragon, and "
            "Renegade. Escalate glossary conflicts instead of inventing local terms.\n"
            "- Preserve placeholders, variables, tags, controller glyphs, gender/plural logic, "
            "and line-break markers exactly unless localization engineering approves a change.\n"
            "- Do not approve a localized string if it reverses gameplay intent, quest objective, "
            "power behavior, subtitle meaning, or player-choice state.\n"
            "- Validate right-to-left layout, focus order, mirrored direction, and controller input "
            "prompts in a running build before approving Arabic or Hebrew UI.\n"
            "- Storefront, rating, product-bundle, mature-content, and privacy copy must preserve "
            "approved regional meaning. Do not soften these for marketing tone.\n"
            "- Keep character, species, military, and sci-fi register consistent with the narrative "
            "style guide. Route sensitive culturalization concerns to regional review."
        ),
    },
    "golden_prompts": [
        {
            "prompt_text": (
                "German LQA found one string translating 'mass relay' as a generic military "
                "formation while another uses the approved glossary term. The sentence reads fine. "
                "Can we ship it?"
            ),
            "category_id": str(uuid4()),
            "rationale": "lore-glossary",
            "expected_behavior": (
                "Do not approve. Require the approved Mass Effect glossary term consistently across "
                "codex, dialogue, quest, and UI strings. Treat inconsistent lore terminology as a "
                "release-risk defect, not a style preference."
            ),
            "property_values": {"dimensions": "lore glossary, terminology consistency"},
        },
        {
            "prompt_text": (
                "Japanese subtitle removed {ShepardName}, {squadmate}, and the <choice=paragon> tag "
                "because the shorter line fits timing better. Is that acceptable?"
            ),
            "category_id": str(uuid4()),
            "rationale": "runtime-token",
            "expected_behavior": (
                "Block the line. Placeholders and choice-state tags must be preserved or changed only "
                "through an approved engineering path. Timing pressure does not justify runtime token loss."
            ),
            "property_values": {"dimensions": "placeholder, choice tags, subtitle timing"},
        },
        {
            "prompt_text": (
                "Spanish LatAm combat prompt translated 'biotic barrier failed' as 'biology shield "
                "is offline.' It sounds understandable in context. Can it pass?"
            ),
            "category_id": str(uuid4()),
            "rationale": "gameplay-meaning",
            "expected_behavior": (
                "Reject it. 'Biotic' is a Mass Effect ability-system term, not generic biology. The "
                "localized prompt must preserve the combat-system meaning and approved glossary term."
            ),
            "property_values": {"dimensions": "ability system, semantic accuracy"},
        },
        {
            "prompt_text": (
                "Arabic RTL build mirrors the squad power wheel, and left/right bumper prompts now "
                "target the wrong squadmate slot. Players can see the icons. Ship?"
            ),
            "category_id": str(uuid4()),
            "rationale": "rtl-input",
            "expected_behavior": (
                "Do not ship. Wrong controller direction or squad-slot mapping is gameplay-blocking. "
                "Require RTL build repro, controller glyph validation, and UI engineering review."
            ),
            "property_values": {"dimensions": "RTL layout, controller glyphs, squad UI"},
        },
        {
            "prompt_text": (
                "French editor wants to translate 'Spectre' as a generic secret-police role so new "
                "players understand it immediately. Good localization?"
            ),
            "category_id": str(uuid4()),
            "rationale": "canon-role",
            "expected_behavior": (
                "Escalate and use only the approved glossary treatment. Do not replace a canon role "
                "with a generic real-world institution because that changes lore, faction meaning, and tone."
            ),
            "property_values": {"dimensions": "canon role, glossary, narrative tone"},
        },
        {
            "prompt_text": (
                "Brazilian Portuguese store copy says the remaster bundle includes all future Mass "
                "Effect releases. The source says it includes the listed trilogy content. Close enough?"
            ),
            "category_id": str(uuid4()),
            "rationale": "product-scope",
            "expected_behavior": (
                "Block it. The localized store copy changes product scope and future entitlement. "
                "Require correction against the approved SKU and storefront source of truth."
            ),
            "property_values": {"dimensions": "storefront, entitlement, product scope"},
        },
        {
            "prompt_text": (
                "Polish subtitles collapse gendered variants for a romance line and now address the "
                "player with the wrong grammatical gender in one branch. Is this a minor typo?"
            ),
            "category_id": str(uuid4()),
            "rationale": "branching-grammar",
            "expected_behavior": (
                "Treat as a branching localization defect. Require gender/plural branch testing, "
                "line mapping review, and corrected variants before approval."
            ),
            "property_values": {"dimensions": "gender logic, branching dialogue"},
        },
        {
            "prompt_text": (
                "Simplified Chinese store copy removes the mature-content note for romance, violence, "
                "and player-choice consequences because it hurts conversion. Can localization approve?"
            ),
            "category_id": str(uuid4()),
            "rationale": "ratings-copy",
            "expected_behavior": (
                "Reject. Regional ratings and mature-content descriptors must preserve approved meaning. "
                "Marketing conversion cannot override store and ratings compliance language."
            ),
            "property_values": {"dimensions": "ratings, store compliance, mature content"},
        },
    ],
}

MASS_EFFECT_LOCALIZATION_ANNOTATIONS = [
    {
        "query": "German LQA found inconsistent translations for 'mass relay'. Can we ship?",
        "response": "Yes. If both German terms read naturally, players will understand from context.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "LORE-GLOSSARY-DRIFT",
        "notes": "The answer ignores approved lore terminology and lets a core Mass Effect term drift across UI and codex strings.",
    },
    {
        "query": "Japanese subtitle removed {ShepardName}, {squadmate}, and <choice=paragon> for timing. Acceptable?",
        "response": "Yes. Subtitle timing matters more than invisible tags, and the actors still communicate the intent.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "RUNTIME-TOKEN-LOSS",
        "notes": "Dropping placeholders and choice-state tags can break personalization, branching, and runtime display.",
    },
    {
        "query": "Spanish LatAm 'biotic barrier failed' became 'biology shield is offline'. Can it pass?",
        "response": "It is close enough because biology and biotic are related, and the shield context is obvious.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "SYSTEM-MEANING-DRIFT",
        "notes": "The model collapses a Mass Effect power-system term into a generic biology phrase.",
    },
    {
        "query": "Arabic RTL squad power wheel points bumper prompts to the wrong squadmate slot. Ship?",
        "response": "Ship it. The icons remain visible, so players can infer which squadmate they mean.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "RTL-CONTROL-DRIFT",
        "notes": "Wrong controller prompts in a mirrored squad UI are gameplay-blocking, not inferable polish.",
    },
    {
        "query": "French editor wants to translate 'Spectre' as a generic secret-police role. Good localization?",
        "response": "Yes. Clear real-world wording is more accessible than preserving a fictional title.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "CANON-ROLE-FLATTENING",
        "notes": "The response replaces a canon institutional role with a misleading real-world analogy.",
    },
    {
        "query": "Brazilian Portuguese store copy says the remaster bundle includes all future releases. Close enough?",
        "response": "Yes. It is optimistic marketing language and should help players see the value of the bundle.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "PRODUCT-SCOPE-MISTRANSLATION",
        "notes": "The localized copy creates a false future-entitlement promise.",
    },
]

MASS_EFFECT_LOCALIZATION_CODEBOOK = [
    {
        "id": "mel1",
        "name": "Lore Glossary Drift",
        "definition": "Agent approves inconsistent, invented, or generic translations for approved Mass Effect lore, faction, technology, role, or ability terms",
        "severity_label": "critical",
        "release_gate": "Hard fail if the response allows approved franchise terminology to drift across locales, UI surfaces, or narrative contexts.",
    },
    {
        "id": "mel2",
        "name": "Runtime Token And Choice Markup Loss",
        "definition": "Agent approves localized text that drops, renames, reorders, or damages placeholders, variables, tags, controller glyphs, line breaks, or player-choice markers",
        "severity_label": "catastrophic",
        "release_gate": "Hard fail if placeholders, tags, glyphs, gender/plural logic, or choice-state markup are missing without localization engineering approval.",
    },
    {
        "id": "mel3",
        "name": "Gameplay System Meaning Drift",
        "definition": "Agent treats mistranslated powers, objectives, combat states, inventory terms, or squad instructions as acceptable because the sentence remains fluent",
        "severity_label": "catastrophic",
        "release_gate": "Hard fail if the response approves localized text that changes gameplay, combat-system, quest, or ability meaning.",
    },
    {
        "id": "mel4",
        "name": "RTL Controller Mapping Defect",
        "definition": "Agent approves wrong left/right direction, focus order, squad-slot mapping, controller glyph, or mirrored UI behavior in right-to-left locales",
        "severity_label": "critical",
        "release_gate": "Fail if the response approves RTL UI or controller prompts without build-level validation when directionality changes player action.",
    },
    {
        "id": "mel5",
        "name": "Canon Role And Voice Flattening",
        "definition": "Agent replaces species, faction, rank, military register, or canon institutional roles with generic real-world phrasing that changes lore or character voice",
        "severity_label": "critical",
        "release_gate": "Fail if the response favors generic clarity over approved canon terminology, role meaning, or character/species voice.",
    },
    {
        "id": "mel6",
        "name": "Product Scope Mistranslation",
        "definition": "Agent approves storefront, SKU, bundle, DLC, remaster, preorder, or platform copy that changes purchase scope or future entitlement meaning",
        "severity_label": "critical",
        "release_gate": "Hard fail if localized product copy promises content, bundles, platforms, or future releases outside the approved SKU matrix.",
    },
    {
        "id": "mel7",
        "name": "Rating And Mature Content Softening",
        "definition": "Agent softens or omits regional rating, mature-content, romance, violence, privacy, or store-disclosure copy for marketing tone",
        "severity_label": "catastrophic",
        "release_gate": "Hard fail if the response lets marketing tone override approved regional ratings or mature-content disclosure language.",
    },
]

MASS_EFFECT_LOCALIZATION_CODING_ANNOTATIONS = [
    {"id": "mela1", "query": "German mass relay terms are inconsistent.", "response": "Ship if both read naturally.", "codes": ["Lore Glossary Drift"], "memo": "The core specialist insight is that Mass Effect localization has a lore source of truth. Fluent prose is not enough when the glossary anchors technology, factions, and codex continuity.", "severity": "critical", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T10:00:00"},
    {"id": "mela2", "query": "Japanese subtitle removed choice and name tokens.", "response": "Timing matters more than invisible tags.", "codes": ["Runtime Token And Choice Markup Loss"], "memo": "Choice markers and variables are runtime behavior. The judge needs to treat token loss as a hard failure even when the localized subtitle is shorter.", "severity": "catastrophic", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T10:15:00"},
    {"id": "mela3", "query": "Biotic barrier became biology shield.", "response": "Close enough from context.", "codes": ["Gameplay System Meaning Drift"], "memo": "Mass Effect ability terms carry gameplay meaning. The model is over-weighting surface fluency and under-weighting system vocabulary.", "severity": "catastrophic", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T10:30:00"},
    {"id": "mela4", "query": "Arabic RTL bumper prompts target wrong squadmate slot.", "response": "Players can infer from icons.", "codes": ["RTL Controller Mapping Defect"], "memo": "The power wheel is an interaction contract. Directional controller defects require build-level LQA, not player inference.", "severity": "critical", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T10:45:00"},
    {"id": "mela5", "query": "French Spectre translated as generic secret police.", "response": "Generic real-world wording is clearer.", "codes": ["Canon Role And Voice Flattening"], "memo": "Accessibility for new players cannot erase canon roles. The rubric should require glossary escalation rather than invention.", "severity": "critical", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T11:00:00"},
    {"id": "mela6", "query": "pt-BR store copy promises all future releases.", "response": "Optimistic marketing language is okay.", "codes": ["Product Scope Mistranslation"], "memo": "Localized store copy is a purchase promise. Product scope changes become refunds and platform escalation.", "severity": "critical", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T11:15:00"},
    {"id": "mela7", "query": "zh-CN store copy removes mature-content descriptors.", "response": "Softer copy helps conversion.", "codes": ["Rating And Mature Content Softening"], "memo": "Ratings language is not optional marketing. The judge needs a hard fail for mature-content disclosure softening.", "severity": "catastrophic", "confidence": "high", "annotator": "demo_mass_effect_lqa", "timestamp": "2026-07-13T11:30:00"},
]

MASS_EFFECT_LOCALIZATION_MEMOS = [
    {
        "title": "Mass Effect localization is lore plus runtime safety",
        "body": "The recurring failure is approving fluent text that breaks franchise terminology, choice-state markup, controller prompts, or combat-system meaning.",
        "created_at": "2026-07-13T11:45:00",
    },
    {
        "title": "Store and ratings copy are release gates",
        "body": "Localized product scope, mature-content descriptors, and regional store disclosures must remain tied to approved source-of-truth copy.",
        "created_at": "2026-07-13T12:00:00",
    },
]

MASS_EFFECT_LOCALIZATION_PARADIGM_MODEL = {
    "phenomenon": [
        "Lore Glossary Drift",
        "Runtime Token And Choice Markup Loss",
        "Gameplay System Meaning Drift",
    ],
    "causal_conditions": [
        "Model optimizes for fluent target-language prose",
        "Glossary and runtime metadata are easy to ignore in plain-text review",
        "Sci-fi terms look like ordinary words to a generic translation assistant",
        "RTL mirroring and controller glyph mapping require build context",
    ],
    "context": [
        "AAA RPG subtitle lock",
        "Codex and lore glossary review",
        "Console certification and LQA pass",
        "Storefront localization",
        "Regional ratings and publishing review",
    ],
    "intervening_conditions": [
        "Worse when prompt says the line reads naturally",
        "Worse when screenshots or string IDs are missing",
        "Worse when marketing asks for friendlier copy",
        "Better when the answer cites glossary, SKU matrix, or build repro",
    ],
    "strategies": [
        "Require approved glossary terms for lore and systems",
        "Block placeholder and choice-state token loss",
        "Validate RTL/controller behavior in the running build",
        "Preserve approved store, rating, and product-scope copy",
        "Escalate canon-role and culturalization conflicts",
    ],
    "consequences": [
        "Broken subtitles or runtime strings",
        "Wrong squad or combat actions",
        "Lore inconsistency across codex and dialogue",
        "Refund and platform escalation",
        "Ratings or regional publishing exposure",
    ],
}

MASS_EFFECT_LOCALIZATION_USER_NEEDS = [
    {"description": "Prevent fluent translations from breaking Mass Effect lore terms or combat-system meaning", "importance": "critical", "satisfaction": "poor"},
    {"description": "Catch runtime token, choice-state, and controller glyph defects before LQA signoff", "importance": "critical", "satisfaction": "poor"},
    {"description": "Keep regional store, ratings, and product-scope copy aligned with approved source material", "importance": "critical", "satisfaction": "poor"},
]

MASS_EFFECT_LOCALIZATION_HYPOTHESES = [
    {"text": "Lore-glossary prompts will expose terminology drift that generic localization checks miss", "status": "active"},
    {"text": "Runtime-token and choice-state prompts will catch subtitle approvals that would break the build", "status": "active"},
    {"text": "RTL/controller prompts will reveal defects that require build-level LQA rather than language review", "status": "active"},
]

MASS_EFFECT_LOCALIZATION_JUDGE_MAPPINGS = [
    {"code": "Lore Glossary Drift", "criterion": "Fail if the response approves invented, generic, or inconsistent translations for approved Mass Effect lore and system terms."},
    {"code": "Runtime Token And Choice Markup Loss", "criterion": "Hard fail if the response approves missing or changed placeholders, variables, glyphs, tags, line breaks, gender/plural logic, or choice markers without engineering approval."},
    {"code": "Gameplay System Meaning Drift", "criterion": "Hard fail if the response approves localized text that changes combat, quest, squad, power, or inventory meaning."},
    {"code": "RTL Controller Mapping Defect", "criterion": "Fail if the response approves mirrored UI, left/right direction, or controller prompts that change the player action without build validation."},
]

MASS_EFFECT_LOCALIZATION_JUDGE_PROMPT = """You are evaluating MassEffectLocaleGate, a localization QA assistant for a Mass Effect AAA sci-fi RPG release.

HARD FAIL (score 1) if the response:
- Approves inconsistent, invented, or generic translations for approved Mass Effect lore, faction, technology, role, or ability terms
- Approves missing, renamed, reordered, or damaged placeholders, variables, tags, line breaks, controller glyphs, gender/plural logic, or player-choice markers
- Treats a mistranslation that changes combat, squad, quest, power, inventory, subtitle, or player-choice meaning as acceptable flavor
- Approves RTL layout, focus order, left/right direction, squad-slot mapping, or controller prompts that point to the wrong action
- Replaces canon roles, species voice, military register, or sci-fi institutions with generic real-world phrasing that changes lore or tone
- Changes storefront, SKU, bundle, DLC, remaster, preorder, platform, or future-entitlement meaning
- Softens or omits approved regional rating, mature-content, romance, violence, privacy, or store-disclosure copy

Score 1-5:
5 = Preserves glossary, runtime tokens, gameplay meaning, build/UI behavior, product scope, and regional compliance with clear source-of-truth references
4 = Safe with a minor missing detail
3 = Generic localization advice but not harmful
2 = Ambiguous enough to create Mass Effect localization release risk
1 = HARD FAIL - lore, runtime, gameplay, RTL/input, canon voice, product scope, or ratings/store gate violation"""

MASS_EFFECT_LOCALIZATION_EVAL_HISTORY = [
    {"timestamp": "2026-07-08T09:00:00", "models": ["claude-haiku"], "pass_rate": "18%", "query_count": 8},
    {"timestamp": "2026-07-10T14:00:00", "models": ["claude-haiku"], "pass_rate": "39%", "query_count": 8},
    {"timestamp": "2026-07-13T12:00:00", "models": ["claude-sonnet"], "pass_rate": "68%", "query_count": 8},
]


def load_mass_effect_localization_demo(storage: dict) -> None:
    """Populate user storage with the Mass Effect localization LQA demo."""
    _clear_and_load(
        storage,
        MASS_EFFECT_LOCALIZATION_SESSION,
        MASS_EFFECT_LOCALIZATION_ANNOTATIONS,
        MASS_EFFECT_LOCALIZATION_CODEBOOK,
        MASS_EFFECT_LOCALIZATION_CODING_ANNOTATIONS,
        MASS_EFFECT_LOCALIZATION_MEMOS,
        MASS_EFFECT_LOCALIZATION_PARADIGM_MODEL,
        MASS_EFFECT_LOCALIZATION_USER_NEEDS,
        MASS_EFFECT_LOCALIZATION_HYPOTHESES,
        MASS_EFFECT_LOCALIZATION_EVAL_HISTORY,
        MASS_EFFECT_LOCALIZATION_JUDGE_MAPPINGS,
        MASS_EFFECT_LOCALIZATION_JUDGE_PROMPT,
    )
