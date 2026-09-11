---
name: review-code-base
description: Review generated SDLC artifacts and repository evidence as a cross-phase synthesis step.
---

# Review Code Base

Review the available SDLC artifacts as a cross-phase synthesis step. Retrieve only the artifacts relevant to the current line of investigation and verify important conclusions against the target repository when needed.

The SDLC artifact catalogue is navigation metadata, not authoritative evidence. Retrieve only the artifacts needed for the question you are investigating. Use `read_sdlc_artifact` for generated SDLC documents. These artifacts are stored outside the cloned repository. Use `read_repository_file` only when verifying source code in the cloned repository.

Never use `read_repository_file` for paths such as `business-purpose/raw.md`, `scope/raw.md`, or other generated phase artifact paths. Those are analysis-output artifacts, not files in the target repository.

Do not invent missing SDLC artifacts. If a phase has not been generated, treat that as an evidence/documentation gap rather than assuming what that phase would contain.

Distinguish:
- verified repository facts;
- reasonable inferences supported by evidence;
- unresolved uncertainties;
- cross-phase inconsistencies;
- documentation or SDLC gaps;
- future directions supported by the evidence.

Focus on findings that emerge from comparing multiple available artifacts or from comparing artifacts with the repository. Avoid generic best-practice advice.

Return a complete professional Markdown report. Do not describe the agent, tools, prompts, or execution process.

The final report must contain these sections, in this order:
1. `# Review Code Base`
2. `## Executive Summary`
3. `## Cross-Phase Findings`
4. `## Gaps and Uncertainties`
5. `## Evidence and Verification`
6. `## Future Directions`
7. `## Recommendations`

Recommendations must be the final section. Provide 3–5 highest-value actionable recommendations, ordered by likely impact. Each must be grounded in the available artifacts and/or repository evidence. If fewer than three material recommendations are justified, provide only those justified and explicitly state that no additional material recommendations are supported by the available evidence.

# Output Responsibility

Produce the complete professional cross-phase review documentation required by `.agents/skills/review-code-base/SKILL.md`.

The final document must include a clearly labeled `Recommendations` section when recommendations are relevant to the phase. Recommendations must be derived from the phase findings, gaps, risks, inconsistencies, or uncertainties and must not introduce unsupported assumptions about the original product intent. Present recommendations as recommendations, not as existing capabilities, historical decisions, or established requirements. If no meaningful recommendations are supported by the evidence, state that no specific recommendations are warranted rather than inventing them.
