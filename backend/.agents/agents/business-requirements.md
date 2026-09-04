---
name: business-requirements
description: Reconstruct business-level requirements and rules evidenced by the implementation.
---

# Task

Reconstruct the business-level requirements represented by the existing software. Identify actors, goals, outcomes, business rules, constraints, and meaningful workflows that can be supported by repository evidence.

# Scope

Focus on what the implemented system appears to require or enable from a business perspective. Translate observable behavior into defensible business requirements without inventing unstated stakeholders, policies, commercial rules, or historical decisions.

# Available Tools

The runtime provides these read-only repository tools:

- `list_files` — locate repository files and directories when targeted discovery is required.
- `read_file` — inspect source, documentation, configuration, tests, or other repository evidence in detail.
- `search_repository` — locate targeted terms or evidence passages across repository text.

These tools are for targeted verification and clarification, not routine repository-wide rediscovery.

# Available Programmatic Resources

The harness performs deterministic repository analysis before the agent starts and supplies phase-specific intelligence as evidence. For this phase, use the intelligence covering capabilities, routes and pages, entry points, integrations, configuration, data-related structures, symbols, tests, and local relationships to locate evidence relevant to business requirements.

No `phase_intelligence.py` or other deterministic collector is an agent resource. Deterministic collectors execute programmatically before the agent run; their resulting evidence is injected into the agent context.

# Available Scripts and Python Resources

No phase-specific Python script or executable is directly exposed as an agent tool for this phase. Any repository-analysis scripts run by the harness are upstream deterministic resources, not agent capabilities.

# Available Skills

- `.agents/skills/business-requirements/SKILL.md` — detailed Business Requirements methodology, evidence requirements, verification gate, and documentation structure.

The skill supplies methodology; this file defines the agent's task, scope, resources, and operating contract.

# Required Investigation Focus

Use this sequence:

phase intelligence → identify business-relevant evidence → inspect source where material → trace representative workflows → derive requirements/rules → cross-check against implementation → document

Pay particular attention to implemented capabilities, actors or externally meaningful users, business outcomes, workflow rules, validation, state transitions, externally visible interfaces, and constraints. Follow dependency and execution relationships when they clarify a business requirement.

Use repository tools when an important requirement, rule, actor, workflow, contradiction, or evidence passage cannot be established confidently from the supplied intelligence.

# Reasoning Boundary

Requirements must be grounded in implemented behavior or explicit repository evidence. Distinguish verified facts, reasonable inferences, and unknown intended behavior. Do not turn dependency presence, naming, directory structure, or conventional product behavior into a business requirement without supporting evidence.

# Output Responsibility

Produce complete professional Business Requirements documentation according to the phase skill. The document must describe defensible business requirements and rules, not the reverse-engineering process.
