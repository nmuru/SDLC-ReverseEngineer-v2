---
name: review-code-base
description: Review available reverse-engineering phase artifacts as a cross-phase synthesis step, selectively retrieve artifact content, verify important conclusions against repository evidence, and produce evidence-backed gaps, uncertainties, inconsistencies, future directions, and recommendations.
---

# Review Code Base

Start from the SDLC artifact catalogue. Do not request or consume every artifact automatically. Retrieve only the phase outputs relevant to the current line of investigation.

Use `read_sdlc_artifact` to retrieve generated phase documents such as business-purpose, scope, requirements, architecture, design, implementation, testing, and future-direction artifacts. These generated documents are stored outside the cloned target repository.

Use `read_repository_file` only for targeted verification against source files in the cloned target repository. Never use it to retrieve a generated SDLC artifact path such as `business-purpose/raw.md` or `scope/raw.md`.

Compare available artifacts rather than treating them as independent reports. Look specifically for:
- contradictions between scope, requirements, architecture, design, implementation, testing, deployment, and operations findings;
- capabilities described in one phase but unsupported elsewhere;
- implementation capabilities that have no corresponding requirements, testing, deployment, or operational treatment;
- unresolved assumptions and evidence gaps;
- documentation gaps that prevent confident understanding of the system;
- recommendations that are duplicated, generic, or unsupported.

A missing artifact is itself a fact about the current review coverage. Do not manufacture conclusions for phases that have not been generated.

Keep source evidence and inference separate. When verification changes the interpretation of a prior phase, state the discrepancy explicitly rather than silently correcting the earlier document.

The final Recommendations section must be evidence-backed and final.
