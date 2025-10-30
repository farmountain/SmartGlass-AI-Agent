# Week 1 Plan

## Goals
- Establish baseline understanding of the SmartGlass AI Agent architecture and dependencies.
- Validate cloud-based contribution workflow by raising at least one pull request.
- Prioritize immediate documentation and onboarding improvements from initial findings.

## Exit Criteria
- A merged or reviewed pull request demonstrating the end-to-end PR workflow.
- Documented insights about onboarding friction and documentation gaps.
- Agreed backlog of next steps for Week 2 based on Week 1 observations.

## Risks
- Limited access to required hardware or cloud services could block validation tasks.
- Unclear ownership may delay PR reviews.
- CI pipeline instability could slow feedback cycles.

## Daily Notes

### Day 1
- Audit existing documentation and tooling to understand current workflows.
- Identify required stakeholders for reviews and approvals.

### Day 2
- Draft updated contribution guidelines reflecting the PR-driven model.
- Inventory CI jobs and note required credentials or secrets.

### Day 3
- Submit a documentation-focused PR through the web interface to validate workflow.
- Capture friction points encountered during submission.

### Day 4
- Review CI feedback from the submitted PR and document remediation steps.
- Coordinate with reviewers to confirm expectations and service-level targets.

### Day 5
- Finalize Week 1 findings and prepare recommendations for Week 2 planning.
- Update roadmap and backlog items based on validated learnings.

## Retro (Paul-Elder + Inversion)

### Purpose
- Capture Week 1 observations about inventory automation, CI bootstrap, and safety scaffolding to inform Week 2 priorities.

### Questions at Issue
- Did the new automation surface legacy risks quickly enough for reviewers to act?
- Were contributors able to rely on the web-only workflow without local tooling?

### Information
- Inventory artifacts: `artifacts/inventory.json` and `docs/INVENTORY.md` summarise file stats and flags.
- CI summary: GitHub Actions `CI` workflow reports lint/test outcomes plus telemetry, bench, and red-team artifacts.

### Assumptions Tested
- Repository layout assumptions (scripts/, docs/, src/) remained stable enough for inventory automation.
- CI runners could install dependencies and execute the new telemetry/bench/red-team steps without manual secrets.

### Inferences
- Prioritise Week 2 work on VAD/ASR latency now that baseline telemetry exists.
- Schedule documentation updates to expand student LLM guidance based on flagged legacy references.

### Implications
- Contributors should treat legacy model references as blockers; CI now fails on critical findings.
- Artifact-driven reviews accelerate onboarding, so future weeks should keep augmenting the summary tables.

### Inversion
- Top failure mode: missing artifacts leading to unverified CI results.
- Mitigation: Inventory, telemetry, and smoke tests now guarantee artifact production on every run.
