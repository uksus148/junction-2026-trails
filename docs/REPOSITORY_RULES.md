# Repository rules

These rules apply to Murat (`uksus148`), Daniil (`nnatthebest`), and Mukhamed (`dyksookelwe`). Both collaborators have write access. Murat owns the repository and follows the same code review process.

## Main branch protection

The active `main-team-review` ruleset targets the repository's default branch, currently `main`.

| Requirement | GitHub behavior |
|---|---|
| Changes through PRs | Push changes to a task branch and submit a PR |
| One approval | Require at least one independent Approve from a developer with write access |
| Dismiss stale approvals | Reviewable changes require another review |
| Resolve review discussions | Resolve all review threads before merging |
| Squash merge | Merge each PR into main as one commit |
| Linear history | Keep main free of merge commits |
| Deletion protection | Block deletion of the default branch |
| Force-push protection | Block rewriting default-branch history |
| Equal conditions | The bypass list is empty, including for the repository owner |

Use task prefixes such as `feat/`, `fix/`, `docs/`, `infra/`, and `chore/` for new branches. Task branches support normal updates and rebase. For stacked PRs, state the base branch and merge order. After squashing an earlier PR, retarget the next PR to `main` before merging it and check its diff; otherwise it squash-merges into the old stack branch instead of `main`.

## Automated checks

The infrastructure workflow from PR #1 runs for changes under `infra/**`. The author and reviewer check applicable CI results before merging. Required status checks are currently empty in the ruleset because the existing workflow runs conditionally. Add a required status only when it produces a final result for every PR into main.

## Assigning reviews

Every PR requires review and at least one approval from a developer other than its author, including internal changes that affect no other component. When no affected owner other than the author exists, explicitly request another developer with the closest relevant expertise.

Choose reviewers according to the components and integration boundaries affected by the PR. Name those components and the requested review scope in the PR description.

| Area | Owner |
|---|---|
| Java/Spring Boot API, SQL, migrations, shared infrastructure, repository governance, backend-facing integration | Murat (uksus148) |
| React UI, map interaction, frontend behavior, client side of the chat contract | Daniil (nnatthebest) |
| FastAPI agent, intent extraction, Exa, embeddings, agent side of the chat contract | Mukhamed (dyksookelwe) |

- A frontend change that consumes Spring Boot routes or places requests Murat's review of that integration.
- An agent/client chat change requests review from the owner on the other side of that interface.
- A PR affecting multiple service boundaries requests the relevant owners and identifies the part each should check.
- For an internal change owned by its author alone, choose a colleague with the closest relevant expertise for an independent check.
- Murat's assistant reviews within Murat's area. Reviews of agent internals, AI-only intent parsing, or frontend presentation are delegated to the relevant owner.

GitHub requires one independent approval. Shared contract changes also require agreement from the affected owners, recorded in the PR and CLAUDE.md. Authors report actual checks. Reviewers use Approve with non-blocking comments for minor wording and style improvements, and Request changes for material correctness, security, build, or agreed-scope issues. Update the review decision after a blocking finding is fixed.

Day planning and personalization remain deferred under Murat's MVP scope decision. Their owners can prepare and discuss the draft PRs, with implementation and integration acceptance deferred until the required backend and AI-agent capabilities and contract agreement are ready.

## Project context and language

The root CLAUDE.md holds architecture, the shared API contract, and team decisions. Murat's local file provides the initial baseline, translated into English. Each developer compares it with their notes and proposes updates through PRs. Service instructions and short team briefs link to this canonical file.

README describes the project and setup. CONTRIBUTING.md defines commit, PR, and review conventions. This document describes branch protection. Write all repository files and GitHub collaboration content in English.

[Active ruleset](https://github.com/uksus148/junction-2026-trails/rules/27240390).
