## Problem Statement

The eBay Sniper project is functional as a self-hosted internal tool, but it is not yet ready to publish as a public open-source GitHub repository. The current repo state appears optimized for local iteration and private deployment rather than safe external consumption. It lacks a clearly staged open-source release plan covering repository hygiene, contributor-facing docs, CI/release automation, support boundaries, and a durable split between user-safe sample configuration and private runtime state.

Without this work, upstreaming now would create avoidable risk:
- secrets or local-only state could leak into the public repo
- outside users would not know what is supported versus stubbed
- contributors would have no clear setup, testing, or contribution path
- maintainers would inherit support load before the project has basic governance and release discipline

## Solution

Prepare the project for upstream publication as a public GitHub repository through a staged open-source readiness effort.

The public repository should present the project as a usable self-hosted auction monitoring/sniping scaffold with transparent constraints:
- production Browse/search/watch flows work now
- Telegram/web/CLI/MCP interfaces exist now
- actual bid placement remains gated by eBay approval and is intentionally stubbed
- local/private runtime data stays out of version control
- contributors get a clear setup path, support expectations, and contribution workflow
- maintainers get CI, release, issue templates, and policy files so the repo can absorb outside use without chaos

## User Stories

1. As Jay, I want to publish the project without leaking private runtime state, so that the public repo is safe from day one.
2. As Jay, I want the public repo to accurately describe what works and what is still gated by eBay approval, so that users do not assume real bidding is live.
3. As Jay, I want the repo to be installable from a clean checkout, so that first-time users can reproduce the working paths.
4. As Jay, I want sample environment/config files to be safe and complete, so that users can configure the service without seeing my secrets.
5. As Jay, I want local deployment and developer workflows documented, so that future contributors do not need chat history to understand the project.
6. As Jay, I want contributor guidance and issue templates, so that inbound contributions are structured.
7. As Jay, I want CI to enforce the current working behaviors, so that open-source churn does not regress Telegram, scheduler, or search behavior.
8. As Jay, I want license and policy files to match the intended public support model, so that usage terms and expectations are explicit.
9. As Jay, I want the repo to make the eBay approval dependency explicit, so that users understand the difference between shadow mode and real bidding.
10. As a first-time user, I want a README that tells me what the project does, what it does not do yet, and how to run it locally, so that I can evaluate it quickly.
11. As a first-time user, I want a docker-first quickstart, so that I can bring the service up without reading implementation code.
12. As a first-time user, I want CLI, Telegram, web, and MCP examples, so that I can choose an interface quickly.
13. As a first-time user, I want troubleshooting notes for the known tricky areas, so that I can recover from common setup failures.
14. As a contributor, I want a clean test command and expected local workflow, so that I can verify my changes before opening a PR.
15. As a contributor, I want coding, PR, and commit expectations documented, so that my changes line up with project standards.
16. As a contributor, I want to know which features are stubbed by design, so that I do not accidentally “fix” intentional behavior.
17. As a contributor, I want fixtures/tests covering the current Telegram and auction-search edge cases, so that I can refactor safely.
18. As a maintainer, I want issue/PR templates and labels conventions, so that incoming work is easier to triage.
19. As a maintainer, I want CI to verify lint/tests/package health before merge, so that the default branch stays shippable.
20. As a maintainer, I want a release strategy for pre-1.0 builds, so that users know which versions are stable enough to try.
21. As a maintainer, I want the repo to separate product docs from historical build notes, so that public readers do not get internal-only planning noise.
22. As a maintainer, I want a public roadmap/backlog entry for real bidding once eBay approves scope, so that people can track the dependency without guessing.
23. As a maintainer, I want automation around dependency/test health, so that simple regressions are caught before release.
24. As a user, I want the bot’s search/list/watch flows to feel consistent and actionable, so that Telegram can serve as a realistic primary interface.
25. As a user, I want the MCP server to align with the deployed source of truth, so that Hermes and the deployed app do not diverge silently.
26. As a user, I want the project to declare persistence/storage expectations, so that I know where my watch data lives.
27. As a user, I want the public repo to state any operational/legal caveats around eBay API access, so that I understand the constraints before deployment.
28. As an external evaluator, I want the project to have obvious repository hygiene, so that I can trust it enough to try or contribute.

## Implementation Decisions

- The work should treat “open-source readiness” as a productization track, not as one giant cleanup commit.
- The public repository should represent the current system honestly: search/watch/monitoring paths are real; bid placement remains stubbed pending eBay scope approval.
- Private runtime artifacts must be excluded from the public repo, including local databases, local env files, caches, venvs, backup files, and deployment-only state.
- The project should keep one canonical public setup path centered on Docker Compose, with local Python development as a secondary path.
- Repository hygiene should include explicit ignore rules, safe examples, and a pass over tracked files to ensure no local/private artifacts are committed.
- Public docs should distinguish user docs from internal planning/history. Product-facing docs belong in README and dedicated docs pages; internal build notes like application packet materials should stay separate.
- Governance files should include at minimum: license file, contributing guide, security policy, code of conduct, issue templates, and pull request template.
- CI should cover the current high-value seams that already caught real bugs here: scheduler startup, Telegram formatting/polling behavior, search result pricing/rendering, and core watch flows.
- The project should add a reproducible dev/test workflow and basic quality gates before upstreaming rather than after outside users arrive.
- The public roadmap should explicitly call out the eBay approval dependency and the future switch from stubbed bidding to real Offer API bidding.
- The release plan should start conservative (pre-1.0), favoring tagged builds and clear changelog/release notes over premature guarantees.
- The GitHub upstreaming path should include repository creation/normalization, but repository publication itself is downstream of readiness work rather than the first step.

## Testing Decisions

- Good tests should verify externally visible behavior rather than implementation details. The key standard is: if a user exercises CLI, Telegram, MCP, scheduler startup, or web API behavior, regressions should be caught without caring about private method structure.
- The highest-value seams already exist and should remain the primary regression anchors:
  - Telegram command handlers and rendered messages
  - scheduler startup/job registration behavior
  - Browse API result mapping for auction search and watch creation
  - REST API endpoints for status/search/watches
- Open-source readiness work itself should include verification at three levels:
  - repository hygiene checks (ignored/generated/private files excluded)
  - CI test suite execution on clean checkout
  - doc/setup validation from a fresh environment using the documented quickstart
- Prior art in the codebase already includes focused tests for Telegram bot behavior, scheduler behavior, and eBay client behavior; these should be extended rather than replaced.
- CI should run the existing test suite and any added smoke checks on every PR before merge.

## Out of Scope

- Implementing real bid placement before eBay grants `buy.offer.auction`
- Replacing the official eBay API path with browser automation
- Full SaaS multi-user productization
- Advanced branding/marketing site work beyond basic repository polish
- Immediate packaging/distribution to package registries if the repo is not yet stable enough
- Solving every deployment target; one documented Docker-first path is enough for the first public release

## Further Notes

- The current repo already has meaningful working value and should be open-sourced as an honest “self-hosted sniper scaffold with stubbed bidding,” not hidden until every feature is complete.
- The most important upstreaming principle is trustworthiness: no secret leakage, no ambiguity about stubbed behavior, and no mismatch between docs and real current behavior.
- A separate follow-on track may be needed to align the deployed app and MCP connector onto one canonical runtime/store, since that divergence has already surfaced during verification.
- Suggested filename is stable because it describes the workstream rather than a date-bound milestone.