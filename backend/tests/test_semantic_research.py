from pathlib import Path

from app.semantic_research import _phase_prompt, _repository_research_input, _provider_base_url, _clip, write_research_artifact
from app.repository_intelligence import RepositoryIntelligence


def _empty_intelligence() -> RepositoryIntelligence:
    return RepositoryIntelligence(
        schema_version="test",
        root="/tmp/repo",
        file_count=2,
        files=["README.md", "app.py"],
        directories=["."],
        languages={"python": 1},
        technologies=["Python"],
        technology_evidence=[],
        package_scripts={},
        dependencies={},
        dev_dependencies={},
        env_variables=[],
        env_variable_evidence=[],
        routes=[],
        page_files=[],
        api_routes=[],
        entry_points=["app.py"],
        test_files=[],
        config_files=[],
        ci_files=[],
        documentation_files=["README.md"],
        documentation_excerpts={"README.md": "A small example application."},
        integration_files=[],
        dependency_edges=[],
        source_files=[],
        parse_summary={},
    )


def test_provider_urls_are_explicit():
    assert _provider_base_url("openai") == "https://api.openai.com/v1"
    assert _provider_base_url("openrouter") == "https://openrouter.ai/api/v1"


def test_repository_research_input_preserves_high_signal_evidence():
    text = _repository_research_input(_empty_intelligence())
    assert "FILES CONSIDERED: 2" in text
    assert "ENTRY POINTS:" in text
    assert "README.md" in text


def test_research_input_is_bounded():
    assert _clip("x" * 100, 10).endswith("[deterministic intelligence truncated for the research pass]")


def test_business_requirements_has_phase_specific_focus():
    focus = _phase_prompt("business-requirements")
    assert "business rules" in focus
    assert "source files" in focus


def test_research_artifact_is_marked_non_authoritative(tmp_path: Path):
    path = tmp_path / "repository-research.md"
    write_research_artifact(path, kind="repository", phase=None, content="candidate domain")
    text = path.read_text(encoding="utf-8")
    assert "not authoritative evidence" in text
    assert "candidate domain" in text
