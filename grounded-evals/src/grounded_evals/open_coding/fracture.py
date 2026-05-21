from __future__ import annotations

import json

from grounded_evals.ingest.models import AgentSpec
from grounded_evals.llm.client import get_default_client, get_model_id
from grounded_evals.models.core import Category, Code, CodeType, Dimension, Property

FRACTURE_PROMPT = """You are an expert qualitative researcher applying Open Coding methodology to help an AI Agent Product Manager create a comprehensive evaluation dataset.

Given this agent specification, fracture the domain into discrete testable prompt categories. For each category, identify properties (attributes that vary) and dimensions (the range each property can take).

Agent Specification:
- Name: {name}
- Description: {description}
- Capabilities: {capabilities}
- Target Users: {target_users}
- Known Edge Cases: {edge_cases}
- Constraints: {constraints}

Generate 8-15 categories that cover:
1. Happy-path scenarios for each capability
2. Edge cases and boundary conditions
3. Adversarial/off-topic inputs
4. Multi-turn conversation scenarios
5. Ambiguous or underspecified requests
6. Different user personas and emotional states
7. Constraint violation attempts

For each category, provide:
- name: short descriptive label
- definition: one sentence explaining what this category tests
- properties: 2-3 properties with dimensions (low_anchor to high_anchor)
- exemplar_prompts: 2-3 example prompts that would fall in this category

Respond in JSON format:
{{
  "categories": [
    {{
      "name": "...",
      "definition": "...",
      "properties": [
        {{"name": "...", "dimensions": [{{"name": "...", "low_anchor": "...", "high_anchor": "..."}}]}}
      ],
      "exemplar_prompts": ["...", "..."]
    }}
  ]
}}"""


def fracture_domain(agent_spec: AgentSpec) -> list[Category]:
    client = get_default_client()
    model_id = get_model_id()

    prompt = FRACTURE_PROMPT.format(
        name=agent_spec.name,
        description=agent_spec.description,
        capabilities=", ".join(c.name for c in agent_spec.capabilities),
        target_users=", ".join(
            f"{u.name} ({u.description})" for u in agent_spec.target_users
        ),
        edge_cases=", ".join(agent_spec.known_edge_cases),
        constraints=", ".join(agent_spec.constraints),
    )

    message = client.messages.create(
        model=model_id,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            raise ValueError("No JSON object found in response")
        data = json.loads(response_text[json_start:json_end])
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"fracture_domain: failed to parse LLM response — {e}") from e

    categories = []
    for cat_data in data.get("categories", []):
        properties = []
        for prop_data in cat_data.get("properties", []):
            dimensions = [
                Dimension(
                    name=d.get("name", prop_data["name"]),
                    low_anchor=d["low_anchor"],
                    high_anchor=d["high_anchor"],
                )
                for d in prop_data.get("dimensions", [])
            ]
            properties.append(Property(name=prop_data["name"], dimensions=dimensions))

        category = Category(
            name=cat_data["name"],
            definition=cat_data.get("definition", ""),
            properties=properties,
        )

        for exemplar in cat_data.get("exemplar_prompts", []):
            code = Code(
                label=f"{cat_data['name']} - exemplar",
                code_type=CodeType.CONSTRUCTED,
                exemplar_prompts=[exemplar],
            )
            category.code_ids.append(code.id)

        categories.append(category)

    return categories
