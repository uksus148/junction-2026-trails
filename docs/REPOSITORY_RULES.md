# Repository rules

These rules apply to Murat (`uksus148`), Daniil (`nnatthebest`), and Mukhamed (`dyksookelwe`). Both collaborators have write access. Murat owns the repository and follows the same code review process.

## Main branch protection

The active `main-team-review` ruleset targets the repository's default branch, currently `main`.

| Requirement | GitHub behavior |
|---|---|
| Changes through PRs | Push changes to a task branch and submit a PR |
| One approval | Require Approve from another developer with write access |
| Dismiss stale approvals | Reviewable changes require another review |
| Resolve review discussions | Resolve all review threads before merging |
| Squash merge | Merge each PR into main as one commit |
| Linear history | Keep main free of merge commits |
| Deletion protection | Block deletion of the default branch |
| Force-push protection | Block rewriting default-branch history |
| Equal conditions | The bypass list is empty, including for the repository owner |

Use task prefixes such as `feat/`, `fix/`, `docs/`, `infra/`, and `chore/` for new branches. Task branches support normal updates and rebase. For stacked PRs, state the base branch and merge order. After squashing an earlier PR, check the base and diff of the next PR.

## Automated checks

The infrastructure workflow from PR #1 runs for changes under `infra/**`. The author and reviewer check applicable CI results before merging. Required status checks are currently empty in the ruleset because the existing workflow runs conditionally. Add a required status only when it produces a final result for every PR into main.

## Assigning reviews

- Send API and agent changes to the developer whose component consumes the contract.
- Ask a colleague who uses geospatial data or embeddings to review shared database changes.
- Request both colleagues' input on shared rules and the initial API contract.
- Authors report actual checks in the description. Reviewers run the scenario and submit Approve or Request changes. Use `[blocker]` and `[nit]` as described in CONTRIBUTING.md.

GitHub requires one approval. For shared contract decisions, collect the affected owners' responses in the PR discussion and record the agreement in CLAUDE.md.

## Project context and language

The root CLAUDE.md holds architecture, the shared API contract, and team decisions. Murat's local file provides the initial baseline, translated into English. Each developer compares it with their notes and proposes updates through PRs. Service instructions and short team briefs link to this canonical file.

README describes the project and setup. CONTRIBUTING.md defines commit, PR, and review conventions. This document describes branch protection. Write all repository files and GitHub collaboration content in English.

[Active ruleset](https://github.com/uksus148/junction-2026-trails/rules/27240390).
