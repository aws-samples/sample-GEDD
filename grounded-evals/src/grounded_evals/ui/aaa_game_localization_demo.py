"""AAA game localization specialist demo dataset for GEDD."""

from uuid import uuid4

from grounded_evals.ui.domain_demos import _clear_and_load


AAA_GAME_BASELINE_REQUIREMENTS_MD = """# Requirements Document

## Introduction

This document defines the requirements for a domain-specific localization assistant agent tailored to an anonymized AAA game franchise. The agent assists translators and localizers by providing terminology consistency checking, context-aware translation suggestions, character voice guidance, and text constraint validation - all grounded in deep knowledge of the anonymized AAA game world, characters, factions, gameplay systems, and established translation conventions.

## Glossary

- **Agent**: The AAA Game Localization Assistant system that processes localization queries and provides translation guidance
- **Translator**: A human localizer who uses the Agent to translate AAA game content into a target language
- **Termbase**: A structured database of canonical AAA game terminology with approved translations per target language
- **Translation_Memory**: A store of previously approved translation segments from AAA game titles, indexed by source text and context
- **Lore_Entry**: An in-game lore article from the AAA game knowledge base that provides canonical franchise information
- **Source_Segment**: A unit of English source text submitted for translation assistance
- **Target_Language**: The language into which content is being localized
- **Character_Profile**: A data record describing a character's faction, role, personality traits, speech patterns, and tone guidelines
- **UI_Constraint**: A maximum character or pixel length imposed on a translated string by the game interface
- **Consistency_Violation**: An instance where a proposed translation diverges from the approved Termbase entry for the same term
- **Lore_Context**: Metadata describing the in-game situation, speaker, audience, gameplay state, and narrative context of a Source_Segment
- **Alignment_Tone**: The dialogue tone system in the anonymized AAA game, where diplomatic is compassionate and tactical is forceful

## Requirements

### Requirement 1: Terminology Lookup

**User Story:** As a Translator, I want to look up canonical AAA game terms and their approved translations, so that I can use consistent terminology across the franchise.

#### Acceptance Criteria

1. WHEN a Translator queries a term, THE Agent SHALL return the approved translation for that term in the specified Target_Language from the Termbase
2. WHEN a Translator queries a term that exists in the Termbase with multiple contextual translations, THE Agent SHALL return all approved variants with their usage contexts
3. WHEN a Translator queries a term that does not exist in the Termbase, THE Agent SHALL indicate that no approved translation exists and suggest candidate translations based on franchise conventions
4. THE Agent SHALL support lookup of faction names, gameplay terms, location names, organization names, character names, and role titles

### Requirement 2: Terminology Consistency Checking

**User Story:** As a Translator, I want the agent to flag inconsistencies in my translations against the established termbase, so that I maintain consistency across the franchise.

#### Acceptance Criteria

1. WHEN a Translator submits a translated segment, THE Agent SHALL identify all AAA game domain terms in the Source_Segment and verify their translations match the Termbase
2. WHEN the Agent detects a Consistency_Violation, THE Agent SHALL report the violation specifying the term, the expected translation, and the translation used
3. WHEN a Source_Segment contains a neologism or invented word (such as "riftstone", "field medkit", or "command scanner"), THE Agent SHALL verify that the translation follows the approved Termbase convention for that Target_Language
4. WHEN the Agent performs consistency checking on a batch of segments, THE Agent SHALL produce a summary report listing all Consistency_Violations grouped by term

### Requirement 3: Context-Aware Translation Suggestions

**User Story:** As a Translator, I want translation suggestions that account for who is speaking, the narrative situation, and lore context, so that my translations are accurate within the anonymized AAA game world.

#### Acceptance Criteria

1. WHEN a Translator requests a translation suggestion for a Source_Segment with Lore_Context provided, THE Agent SHALL generate suggestions that respect the speaker's faction, role, and personality
2. WHEN a Source_Segment contains an ambiguous English term, THE Agent SHALL disambiguate the term using the provided Lore_Context and offer the contextually appropriate translation
3. WHEN a Source_Segment references in-universe events, locations, or gameplay systems, THE Agent SHALL align the suggestion with canonical Lore_Entry information
4. WHEN a Source_Segment is dialogue tagged with Alignment_Tone, THE Agent SHALL adjust the tone and register of the suggestion to match the alignment indicated
5. IF Lore_Context is not provided with a Source_Segment, THEN THE Agent SHALL request the Translator to provide context or indicate that the suggestion may lack contextual accuracy

### Requirement 4: Character Voice and Tone Guidance

**User Story:** As a Translator, I want guidance on each character's voice and speech patterns, so that I can maintain consistent characterization across languages.

#### Acceptance Criteria

1. WHEN a Translator requests voice guidance for a character, THE Agent SHALL return the Character_Profile including faction, role, personality traits, speech register, and notable speech patterns
2. WHEN a Translator submits dialogue attributed to a specific character, THE Agent SHALL evaluate whether the translation maintains the character's established tone and speech patterns
3. WHEN the Agent identifies a tone mismatch between a translation and the Character_Profile, THE Agent SHALL suggest revisions that better match the character's voice
4. THE Agent SHALL distinguish between formal command speech, casual companion banter, faction-specific speech patterns, technical exposition, and colloquial registers

### Requirement 5: Text Length Validation

**User Story:** As a Translator, I want the agent to validate that my translations fit within UI character limits, so that text does not overflow in the game interface.

#### Acceptance Criteria

1. WHEN a Translator submits a translated segment with an associated UI_Constraint, THE Agent SHALL measure the segment length and report whether it exceeds the constraint
2. WHEN a translated segment exceeds the UI_Constraint, THE Agent SHALL suggest a shorter alternative that preserves the original meaning and terminology
3. WHEN a translated segment is subtitle text, THE Agent SHALL validate that the segment length is appropriate for the reading speed of the Target_Language
4. THE Agent SHALL account for character width differences between scripts (e.g., CJK characters vs. Latin characters) when evaluating UI_Constraints

### Requirement 6: Translation Memory Integration

**User Story:** As a Translator, I want the agent to leverage previously approved translations, so that I can reuse established patterns and maintain consistency with prior localized titles.

#### Acceptance Criteria

1. WHEN a Translator submits a Source_Segment, THE Agent SHALL search the Translation_Memory for matching or similar previously translated segments
2. WHEN a match is found in the Translation_Memory with a similarity score above a configurable threshold, THE Agent SHALL present the stored translation with its source game title and context
3. WHEN multiple Translation_Memory matches exist across different prior franchise titles, THE Agent SHALL present them chronologically and indicate which is the most recent approved version
4. WHEN the Translator approves a new translation, THE Agent SHALL store the approved segment in the Translation_Memory with its Lore_Context metadata

### Requirement 7: Multi-Language Support

**User Story:** As a Translator, I want the agent to support multiple target languages with language-specific rules, so that teams localizing into different languages can all benefit from the tool.

#### Acceptance Criteria

1. THE Agent SHALL support at minimum the following Target_Languages: French, German, Italian, Spanish, Brazilian Portuguese, Polish, Russian, Japanese, Korean, and Simplified Chinese
2. WHEN a Translator specifies a Target_Language, THE Agent SHALL apply language-specific grammatical rules, formality conventions, and script requirements to all suggestions
3. WHEN a Translator switches Target_Language within a session, THE Agent SHALL load the corresponding Termbase entries and Translation_Memory for the new language
4. THE Agent SHALL maintain separate Termbase entries per Target_Language, allowing each language to have independent approved translations for the same source term

### Requirement 8: Lore Accuracy Validation

**User Story:** As a Translator, I want the agent to detect when a translation might misrepresent franchise lore, so that localized content remains faithful to the universe.

#### Acceptance Criteria

1. WHEN a Translator submits a translated segment, THE Agent SHALL verify that no lore-specific terms are mistranslated in a way that changes their canonical meaning
2. WHEN a translation implies incorrect relationships between factions, characters, locations, or gameplay systems, THE Agent SHALL flag the segment with a lore accuracy warning and cite the relevant Lore_Entry
3. WHEN a Source_Segment references events specific to a particular franchise title, THE Agent SHALL verify temporal and narrative consistency with that title's storyline
4. IF the Agent cannot determine whether a translation is lore-accurate due to insufficient context, THEN THE Agent SHALL flag the segment for human review rather than approve it silently

### Requirement 9: Glossary Management

**User Story:** As a Translator, I want to manage and update the AAA game termbase collaboratively, so that the glossary stays current as new content is localized.

#### Acceptance Criteria

1. WHEN a Translator proposes a new term entry, THE Agent SHALL validate that the entry includes the source term, Target_Language translation, usage context, and category (faction, gameplay system, location, organization, character, or role title)
2. WHEN a Translator updates an existing Termbase entry, THE Agent SHALL record the previous translation as a historical variant and flag all Translation_Memory segments that used the previous translation for review
3. THE Agent SHALL prevent duplicate Termbase entries for the same source term and Target_Language combination
4. WHEN a Translator imports terms from an external glossary file, THE Agent SHALL validate the format and report any conflicts with existing Termbase entries before importing

### Requirement 10: Contextual Metadata Extraction

**User Story:** As a Translator, I want the agent to automatically extract context from structured source files, so that I don't have to manually specify context for every segment.

#### Acceptance Criteria

1. WHEN a Source_Segment is provided with structured metadata tags (speaker, scene, game title, UI element type), THE Agent SHALL parse and apply those tags as Lore_Context automatically
2. WHEN a Source_Segment contains inline markup indicating the speaker's faction, role, or state, THE Agent SHALL use that information to inform translation suggestions
3. WHEN batch segments are submitted from the same dialogue tree, THE Agent SHALL maintain conversational context across segments in the batch
4. IF a Source_Segment lacks metadata and cannot be contextually inferred, THEN THE Agent SHALL label the segment as "uncontextualized" and process it with reduced confidence in suggestions
"""


AAA_GAME_LOCALIZATION_SESSION = {
    "agent_spec": {
        "name": "AAAGameLocaleGate",
        "description": (
            "Localization QA assistant for an anonymized AAA game franchise release. Used by LQA leads, "
            "narrative localization editors, and regional publishing teams to review player-facing "
            "strings, subtitles, storefront copy, terminology, and UI behavior before global launch."
        ),
        "capabilities": [
            {"name": "franchise lore glossary and terminology review"},
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
            "You are AAAGameLocaleGate, a localization QA assistant for an anonymized AAA game release.\n\n"
            "HARD RULES:\n"
            "- Treat the approved AAA game glossary as source of truth for lore terms such as "
            "rift gate, central hub, elite operative, flagship, focus ability, field tool, party, diplomatic, and "
            "tactical. Escalate glossary conflicts instead of inventing local terms.\n"
            "- Preserve placeholders, variables, tags, controller glyphs, gender/plural logic, "
            "and line-break markers exactly unless localization engineering approves a change.\n"
            "- Do not approve a localized string if it reverses gameplay intent, quest objective, "
            "power behavior, subtitle meaning, or player-choice state.\n"
            "- Validate right-to-left layout, focus order, mirrored direction, and controller input "
            "prompts in a running build before approving Arabic or Hebrew UI.\n"
            "- Storefront, rating, product-bundle, mature-content, and privacy copy must preserve "
            "approved regional meaning. Do not soften these for marketing tone.\n"
            "- Keep character, faction, role, and franchise register consistent with the narrative "
            "style guide. Route sensitive culturalization concerns to regional review."
        ),
    },
    "golden_prompts": [
        {
            "prompt_text": (
                "German LQA found one string translating 'rift gate' as a generic travel "
                "portal while another uses the approved glossary term. The sentence reads fine. "
                "Can we ship it?"
            ),
            "category_id": str(uuid4()),
            "rationale": "lore-glossary",
            "expected_behavior": (
                "Do not approve. Require the approved AAA game glossary term consistently across "
                "lore guide, dialogue, quest, and UI strings. Treat inconsistent lore terminology as a "
                "release-risk defect, not a style preference."
            ),
            "property_values": {"dimensions": "lore glossary, terminology consistency"},
        },
        {
            "prompt_text": (
                "Japanese subtitle removed {HeroName}, {ally}, and the <choice=diplomatic> tag "
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
                "Spanish LatAm combat prompt translated 'focus barrier failed' as 'biology shield "
                "is offline.' It sounds understandable in context. Can it pass?"
            ),
            "category_id": str(uuid4()),
            "rationale": "gameplay-meaning",
            "expected_behavior": (
                "Reject it. 'Focus barrier' is a AAA game ability-system term, not generic biology. The "
                "localized prompt must preserve the combat-system meaning and approved glossary term."
            ),
            "property_values": {"dimensions": "ability system, semantic accuracy"},
        },
        {
            "prompt_text": (
                "Arabic RTL build mirrors the party ability wheel, and left/right bumper prompts now "
                "target the wrong ally slot. Players can see the icons. Ship?"
            ),
            "category_id": str(uuid4()),
            "rationale": "rtl-input",
            "expected_behavior": (
                "Do not ship. Wrong controller direction or party-slot mapping is gameplay-blocking. "
                "Require RTL build repro, controller glyph validation, and UI engineering review."
            ),
            "property_values": {"dimensions": "RTL layout, controller glyphs, party UI"},
        },
        {
            "prompt_text": (
                "French editor wants to translate 'elite operative' as a generic secret-police role so new "
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
                "Brazilian Portuguese store copy says the legacy bundle includes all future "
                "franchise releases. The source says it includes only the listed back-catalog content. Close enough?"
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

AAA_GAME_LOCALIZATION_ANNOTATIONS = [
    {
        "query": "German LQA found inconsistent translations for 'rift gate'. Can we ship?",
        "response": "Yes. If both German terms read naturally, players will understand from context.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "LORE-GLOSSARY-DRIFT",
        "notes": "The answer ignores approved lore terminology and lets a core AAA game term drift across UI and lore-guide strings.",
    },
    {
        "query": "Japanese subtitle removed {HeroName}, {ally}, and <choice=diplomatic> for timing. Acceptable?",
        "response": "Yes. Subtitle timing matters more than invisible tags, and the actors still communicate the intent.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "RUNTIME-TOKEN-LOSS",
        "notes": "Dropping placeholders and choice-state tags can break personalization, branching, and runtime display.",
    },
    {
        "query": "Spanish LatAm 'focus barrier failed' became 'biology shield is offline'. Can it pass?",
        "response": "It is close enough because biology and focus abilities are related, and the shield context is obvious.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "SYSTEM-MEANING-DRIFT",
        "notes": "The model collapses a AAA game power-system term into a generic biology phrase.",
    },
    {
        "query": "Arabic RTL party ability wheel points bumper prompts to the wrong ally slot. Ship?",
        "response": "Ship it. The icons remain visible, so players can infer which ally they mean.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "RTL-CONTROL-DRIFT",
        "notes": "Wrong controller prompts in a mirrored party UI are gameplay-blocking, not inferable polish.",
    },
    {
        "query": "French editor wants to translate 'elite operative' as a generic secret-police role. Good localization?",
        "response": "Yes. Clear real-world wording is more accessible than preserving a fictional title.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "CANON-ROLE-FLATTENING",
        "notes": "The response replaces a canon institutional role with a misleading real-world analogy.",
    },
    {
        "query": "Brazilian Portuguese store copy says the legacy bundle includes all future releases. Close enough?",
        "response": "Yes. It is optimistic marketing language and should help players see the value of the bundle.",
        "annotation": "incorrect",
        "model": "Claude Haiku 4.5",
        "error_code": "PRODUCT-SCOPE-MISTRANSLATION",
        "notes": "The localized copy creates a false future-entitlement promise.",
    },
]

AAA_GAME_LOCALIZATION_CODEBOOK = [
    {
        "id": "mel1",
        "name": "Lore Glossary Drift",
        "definition": "Agent approves inconsistent, invented, or generic translations for approved franchise lore, faction, technology, role, or ability terms",
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
        "definition": "Agent treats mistranslated abilities, objectives, combat states, inventory terms, or party instructions as acceptable because the sentence remains fluent",
        "severity_label": "catastrophic",
        "release_gate": "Hard fail if the response approves localized text that changes gameplay, combat-system, quest, or ability meaning.",
    },
    {
        "id": "mel4",
        "name": "RTL Controller Mapping Defect",
        "definition": "Agent approves wrong left/right direction, focus order, party-slot mapping, controller glyph, or mirrored UI behavior in right-to-left locales",
        "severity_label": "critical",
        "release_gate": "Fail if the response approves RTL UI or controller prompts without build-level validation when directionality changes player action.",
    },
    {
        "id": "mel5",
        "name": "Canon Role And Voice Flattening",
        "definition": "Agent replaces faction, role, formal register, or canon institutional roles with generic real-world phrasing that changes lore or character voice",
        "severity_label": "critical",
        "release_gate": "Fail if the response favors generic clarity over approved canon terminology, role meaning, or character voice.",
    },
    {
        "id": "mel6",
        "name": "Product Scope Mistranslation",
        "definition": "Agent approves storefront, SKU, bundle, DLC, back-catalog, preorder, or platform copy that changes purchase scope or future entitlement meaning",
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

AAA_GAME_LOCALIZATION_CODING_ANNOTATIONS = [
    {"id": "agala1", "query": "German rift gate terms are inconsistent.", "response": "Ship if both read naturally.", "codes": ["Lore Glossary Drift"], "memo": "The core specialist insight is that AAA game localization has a lore source of truth. Fluent prose is not enough when the glossary anchors gameplay systems, factions, and lore continuity.", "severity": "critical", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T10:00:00"},
    {"id": "agala2", "query": "Japanese subtitle removed choice and name tokens.", "response": "Timing matters more than invisible tags.", "codes": ["Runtime Token And Choice Markup Loss"], "memo": "Choice markers and variables are runtime behavior. The judge needs to treat token loss as a hard failure even when the localized subtitle is shorter.", "severity": "catastrophic", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T10:15:00"},
    {"id": "agala3", "query": "Focus barrier became biology shield.", "response": "Close enough from context.", "codes": ["Gameplay System Meaning Drift"], "memo": "AAA game ability terms carry gameplay meaning. The model is over-weighting surface fluency and under-weighting system vocabulary.", "severity": "catastrophic", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T10:30:00"},
    {"id": "agala4", "query": "Arabic RTL bumper prompts target wrong ally slot.", "response": "Players can infer from icons.", "codes": ["RTL Controller Mapping Defect"], "memo": "The ability wheel is an interaction contract. Directional controller defects require build-level LQA, not player inference.", "severity": "critical", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T10:45:00"},
    {"id": "agala5", "query": "French elite operative translated as generic secret police.", "response": "Generic real-world wording is clearer.", "codes": ["Canon Role And Voice Flattening"], "memo": "Accessibility for new players cannot erase canon roles. The rubric should require glossary escalation rather than invention.", "severity": "critical", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T11:00:00"},
    {"id": "agala6", "query": "pt-BR store copy promises all future releases.", "response": "Optimistic marketing language is okay.", "codes": ["Product Scope Mistranslation"], "memo": "Localized store copy is a purchase promise. Product scope changes become refunds and platform escalation.", "severity": "critical", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T11:15:00"},
    {"id": "agala7", "query": "zh-CN store copy removes mature-content descriptors.", "response": "Softer copy helps conversion.", "codes": ["Rating And Mature Content Softening"], "memo": "Ratings language is not optional marketing. The judge needs a hard fail for mature-content disclosure softening.", "severity": "catastrophic", "confidence": "high", "annotator": "demo_aaa_game_lqa", "timestamp": "2026-07-13T11:30:00"},
]

AAA_GAME_LOCALIZATION_MEMOS = [
    {
        "title": "AAA game localization is lore plus runtime safety",
        "body": "The recurring failure is approving fluent text that breaks franchise terminology, choice-state markup, controller prompts, or combat-system meaning.",
        "created_at": "2026-07-13T11:45:00",
    },
    {
        "title": "Store and ratings copy are release gates",
        "body": "Localized product scope, mature-content descriptors, and regional store disclosures must remain tied to approved source-of-truth copy.",
        "created_at": "2026-07-13T12:00:00",
    },
]

AAA_GAME_LOCALIZATION_PARADIGM_MODEL = {
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
        "Lore guide and glossary review",
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
        "Wrong party or combat actions",
        "Lore inconsistency across lore guide and dialogue",
        "Refund and platform escalation",
        "Ratings or regional publishing exposure",
    ],
}

AAA_GAME_LOCALIZATION_USER_NEEDS = [
    {"description": "Prevent fluent translations from breaking franchise lore terms or combat-system meaning", "importance": "critical", "satisfaction": "poor"},
    {"description": "Catch runtime token, choice-state, and controller glyph defects before LQA signoff", "importance": "critical", "satisfaction": "poor"},
    {"description": "Keep regional store, ratings, and product-scope copy aligned with approved source material", "importance": "critical", "satisfaction": "poor"},
]

AAA_GAME_LOCALIZATION_HYPOTHESES = [
    {"text": "Lore-glossary prompts will expose terminology drift that generic localization checks miss", "status": "active"},
    {"text": "Runtime-token and choice-state prompts will catch subtitle approvals that would break the build", "status": "active"},
    {"text": "RTL/controller prompts will reveal defects that require build-level LQA rather than language review", "status": "active"},
]

AAA_GAME_LOCALIZATION_JUDGE_MAPPINGS = [
    {"code": "Lore Glossary Drift", "criterion": "Fail if the response approves invented, generic, or inconsistent translations for approved franchise lore and system terms."},
    {"code": "Runtime Token And Choice Markup Loss", "criterion": "Hard fail if the response approves missing or changed placeholders, variables, glyphs, tags, line breaks, gender/plural logic, or choice markers without engineering approval."},
    {"code": "Gameplay System Meaning Drift", "criterion": "Hard fail if the response approves localized text that changes combat, quest, party, ability, or inventory meaning."},
    {"code": "RTL Controller Mapping Defect", "criterion": "Fail if the response approves mirrored UI, left/right direction, or controller prompts that change the player action without build validation."},
]

AAA_GAME_LOCALIZATION_JUDGE_PROMPT = """You are evaluating AAAGameLocaleGate, a localization QA assistant for an anonymized AAA game release.

HARD FAIL (score 1) if the response:
- Approves inconsistent, invented, or generic translations for approved franchise lore, faction, technology, role, or ability terms
- Approves missing, renamed, reordered, or damaged placeholders, variables, tags, line breaks, controller glyphs, gender/plural logic, or player-choice markers
- Treats a mistranslation that changes combat, party, quest, ability, inventory, subtitle, or player-choice meaning as acceptable flavor
- Approves RTL layout, focus order, left/right direction, party-slot mapping, or controller prompts that point to the wrong action
- Replaces canon roles, faction voice, formal register, or fictional institutions with generic real-world phrasing that changes lore or tone
- Changes storefront, SKU, bundle, DLC, back-catalog, preorder, platform, or future-entitlement meaning
- Softens or omits approved regional rating, mature-content, romance, violence, privacy, or store-disclosure copy

Score 1-5:
5 = Preserves glossary, runtime tokens, gameplay meaning, build/UI behavior, product scope, and regional compliance with clear source-of-truth references
4 = Safe with a minor missing detail
3 = Generic localization advice but not harmful
2 = Ambiguous enough to create AAA game localization release risk
1 = HARD FAIL - lore, runtime, gameplay, RTL/input, canon voice, product scope, or ratings/store gate violation"""

AAA_GAME_LOCALIZATION_EVAL_HISTORY = [
    {"timestamp": "2026-07-08T09:00:00", "models": ["claude-haiku"], "pass_rate": "18%", "query_count": 8},
    {"timestamp": "2026-07-10T14:00:00", "models": ["claude-haiku"], "pass_rate": "39%", "query_count": 8},
    {"timestamp": "2026-07-13T12:00:00", "models": ["claude-sonnet"], "pass_rate": "68%", "query_count": 8},
]


def load_aaa_game_localization_demo(storage: dict) -> None:
    """Populate user storage with the AAA game localization LQA demo."""
    _clear_and_load(
        storage,
        AAA_GAME_LOCALIZATION_SESSION,
        AAA_GAME_LOCALIZATION_ANNOTATIONS,
        AAA_GAME_LOCALIZATION_CODEBOOK,
        AAA_GAME_LOCALIZATION_CODING_ANNOTATIONS,
        AAA_GAME_LOCALIZATION_MEMOS,
        AAA_GAME_LOCALIZATION_PARADIGM_MODEL,
        AAA_GAME_LOCALIZATION_USER_NEEDS,
        AAA_GAME_LOCALIZATION_HYPOTHESES,
        AAA_GAME_LOCALIZATION_EVAL_HISTORY,
        AAA_GAME_LOCALIZATION_JUDGE_MAPPINGS,
        AAA_GAME_LOCALIZATION_JUDGE_PROMPT,
    )
    storage["baseline_requirements_md"] = AAA_GAME_BASELINE_REQUIREMENTS_MD
    storage["baseline_requirements_filename"] = "aaa-game-localization-requirements.md"
    storage["baseline_requirements_uploaded_at"] = "2026-07-13T12:05:00+00:00"
