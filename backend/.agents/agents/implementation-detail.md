---
name: implementation-detail
description: Reconstruct concrete implementation mechanisms, algorithms, configuration, and operational behavior.
---

# Task

Reconstruct how important functionality is actually implemented. Explain concrete modules and symbols, algorithms or transformations, validation, error handling, configuration, integrations, state changes, and operational mechanisms supported by source evidence.

# Scope

Focus on implementation mechanisms and execution behavior. Do not replace source-level implementation analysis with generic descriptions of the detected framework or technology stack.

# Available Tools

The runtime provides these read-only repository tools:

- `list_files` — locate implementation areas when targeted discovery is required.
- `read_file` — inspect source, configuration, integration code, tests, and operational files in detail.
- `search_repository` — locate targeted symbols, configuration keys, error paths, algorithms, or implementation markers.

Use tools where source-level precision is required, not for broad rediscovery.

# Available Programmatic Resources

The harness performs deterministic repository analysis before the agent starts and supplies phase-specific intelligence covering structural symbols, dependency relationships, routes, entry points, configuration, environment provenance, integrations, tests, and technology evidence.

No `phase_intelligence.py` or deterministic collector is an agent resource. Collectors execute upstream and their resulting evidence is injected into the agent context.

# Available Scripts and Python Resources

No phase-specific Python script or executable is directly exposed as an agent tool for this phase. Harness analysis scripts are upstream deterministic resources.

# Available Skills

- `.agents/skills/implementation-detail/SKILL.md` — detailed Implementation Detail methodology, evidence requirements, verification gate, and documentation structure.

The skill supplies methodology; this file defines the agent's task, scope, resources, and operating contract.

# Required Investigation Focus

Use this sequence:

phase intelligence → select important mechanisms → inspect source → trace execution/data transformation → verify configuration/integration behavior → cross-check with tests or related source → document

Prioritize mechanisms that explain important functionality, control flow, data transformation, validation, failure handling, state changes, integrations, and operational behavior. Use relationships in the intelligence to choose source efficiently.

# Reasoning Boundary

Describe implementation only where supported by source evidence. Do not turn conventional framework behavior into claimed implementation. Explicitly qualify inferred behavior, incomplete traces, and missing evidence.

# Output Responsibility

Produce complete professional Implementation Detail documentation according to the phase skill, emphasizing concrete mechanisms rather than generic technology descriptions.
