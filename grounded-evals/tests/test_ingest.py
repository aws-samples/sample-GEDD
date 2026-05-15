from pathlib import Path

from grounded_evals.ingest import parse_agent_spec


def test_parse_agent_spec():
    spec_path = Path(__file__).parent.parent / "configs" / "agent_spec_example.yaml"
    spec = parse_agent_spec(spec_path)

    assert spec.name == "Customer Support Agent"
    assert spec.description == "Handles customer inquiries for an e-commerce platform"
    assert len(spec.capabilities) == 4
    assert spec.capabilities[0].name == "Order status lookup"
    assert len(spec.target_users) == 3
    assert spec.target_users[0].name == "Frustrated customer"
    assert len(spec.known_edge_cases) == 3
    assert len(spec.constraints) == 2


def test_parse_agent_spec_minimal(tmp_path: Path):
    minimal_yaml = tmp_path / "minimal.yaml"
    minimal_yaml.write_text("agent:\n  name: Test Agent\n")
    spec = parse_agent_spec(minimal_yaml)

    assert spec.name == "Test Agent"
    assert spec.capabilities == []
    assert spec.target_users == []
