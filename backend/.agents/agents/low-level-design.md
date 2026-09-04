---
name: low-level-design
description: Reconstruct detailed module, symbol, interface, data, and execution relationships.
---

# Task

Reconstruct the detailed design of important modules and interactions. Explain symbols, interfaces, data structures, control flow, dependencies, validation, error handling, and external boundaries where repository evidence supports them.

# Scope

Focus on module- and symbol-level design and the relationships needed to understand detailed execution. Do not broaden into generic architecture or undocumented implementation intent.

# Available Tools

The runtime provides these read-only repository tools:

- `list_files` — locate relevant implementation modules when targeted discovery is required.
- `read_file` — inspect concrete symbols, interfaces, control flow, and data handling.
- `search_repository` — locate targeted symbols, imports, exports, interfaces, calls, or configuration.

Use tools selectively to obtain precise source evidence.

# Available Programmatic Resources

The harness performs deterministic structural analysis before the agent starts and supplies phase-specific intelligence containing symbols, imports/exports, local dependency relationships, entry points, routes, configuration, integrations, and other detailed evidence.

No `phase_intelligence.py` or deterministic collector is an agent resource. Collectors execute upstream and their resulting evidence is injected into the agent context.

# Available Scripts and Python Resources

No phase-specific Python script or executable is directly exposed as an agent tool for this phase. Harness analysis scripts are upstream deterministic resources.

# Available Skills

- `.agents/skills/low-level-design/SKILL.md` — detailed Low-Level Design methodology, evidence requirements, verification gate, and documentation structure.

The skill supplies methodology; this file defines the agent's task, scope, resources, and operating contract.

# Required Investigation Focus

Use this sequence:

phase intelligence → identify important module/symbol relationships → inspect source → trace execution/data flow → verify interfaces and boundaries → cross-check related source/tests → document

Follow graph relationships to select the most relevant implementation areas. Read source where exact control flow, interface behavior, data transformation, or error handling materially affects the design conclusion.

# Reasoning Boundary

Trace concrete implementation relationships. Do not manufacture internal behavior from naming conventions or framework assumptions. Distinguish verified details, reasonable inferences, and unknowns.

# Output Responsibility

Produce complete professional Low-Level Design documentation according to the phase skill, with precise evidence and diagrams where required.
