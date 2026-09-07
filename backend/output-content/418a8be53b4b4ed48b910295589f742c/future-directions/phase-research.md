# Phase Research Brief

Research schema: 3
Phase: future-directions

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
The future-directions phase exhibits concentrated technical debt in agent skills and generated outputs, with zero parser coverage for tree-sitter analysis and no dedicated test coverage visible for the phase itself. The phase depends on a JSON output contract (phase + documentation), but the supplied intelligence does not confirm automated enforcement of this contract for future-directions specifically, nor does it reveal the prompts driving agent analysis.

Evidence-backed gaps: Agent skills are deprecated across multiple phases—business-purpose, features, implementation-detail, and low-level-design SKILL.md files are marked deprecated—while the future-directions skill itself carries FIXME, deprecated, and TODO markers (backend/.agents/skills/future-directions/SKILL.md). This indicates the phase logic may be stale or under active refactor. Generated outputs contain maintenance markers: vercel-demo/future-directions.md and a667840c54d2401593939d6812f07b73/future-directions/{opencode-output,raw}.md include TODO/FIXME/XXX/HACK, suggesting produced documentation is not yet clean. Parser coverage is absent: tree-sitter attempted 31 files, parsed 0, with 31 unavailable, meaning repository intelligence collection lacks structural parsing for these attempts and may miss symbol-level evidence needed for future-directions analysis.

Testing and validation: Only backend/tests/test_semantic_research.py appears in the intelligence; no future-directions-specific test is evident. The phase relies on agent output contracts, but the intelligence does not confirm automated validation of future-directions outputs against the mandated JSON schema. The backend/output-content directory contains generated sets for multiple work IDs, yet the intelligence does not indicate whether future-directions outputs were validated post-generation.

Brittle boundaries: semantic_research.py carries a TODO and is listed among external-integration risks alongside agent_runner.py. analyzer.py depends on both, creating a coupling chain—analyzer -> agent_runner -> config and analyzer -> semantic_research -> repository_intelligence—so changes to research or runner logic could propagate broadly. experiments/openai_sdk_process_test/test_concurrent_agents.py is flagged as a brittle boundary, indicating concurrency patterns remain experimental rather than production-hardened.

Configuration/CI risks: CI/configuration evidence is limited to requirements.txt, next.config.ts, package.json, and tsconfig.json. No future-directions-specific CI gates or lint rules are visible. Environment variables such as OPENAI_AGENT_TEST_REQUESTS and OPENROUTER_MODEL exist, but their role in future-directions reliability is unspecified.

Uncertainties: Whether deprecated skills are replaced by newer equivalents or abandoned is unclear. The exact cause of tree-sitter unavailability (missing binaries vs. unsupported languages) is not specified. The xxx markers in technology-architecture outputs may indicate placeholders or corrupted generation, but the intelligence does not clarify.

Interpretation: The future-directions phase is operational but carries legacy skill debt and unverified output quality. Zero parser coverage is a structural risk for intelligence gathering, and the absence of phase-specific tests means output contract adherence likely relies on manual or downstream validation rather than automated guarantees.
