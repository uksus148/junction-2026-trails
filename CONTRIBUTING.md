# Contributing

Create a task branch from the current `main` and open a pull request that can be reviewed independently. English is the project language for repository files, code comments, documentation, commit messages, PR titles, descriptions, and reviews.

Read [CLAUDE.md](CLAUDE.md) before making changes. The [repository rules](docs/REPOSITORY_RULES.md) apply to all three developers. GitHub automatically inserts the [PR template](.github/pull_request_template.md).

## Branches and commits

Use descriptive branch names such as `feat/places-bbox`, `fix/route-distance`, `docs/api-contract`, `infra/local-database`, or `chore/dependencies`.

Use Conventional Commits in the format `type(scope): short description`. Start the English description with an imperative verb. Choose a scope from `frontend`, `api`, `agent`, `infra`, or `repo` for shared files.

Use `feat` for new behavior, `fix` for bug fixes, `test` for tests, `docs` for documentation, `refactor` for behavior-preserving restructuring, `ci` for automated checks, and `chore` for maintenance.

```text
feat(api): filter places by bounding box
fix(frontend): show the source link for each photo
test(agent): cover chat requests with no matching places
```

## Pull requests

Use the same format for the PR title and the resulting squash commit. Complete the following sections. State which checks remain outstanding.

```markdown
### What changed
Describe the changed behavior and who uses it.

### Where to start reviewing
Name the first file to open and changes to the API, database schema, or Kafka events.

### How to test
Provide commands or steps, inputs, and actual results.
```

Agree shared API changes with the affected developers before implementation, and record the decision in the root `CLAUDE.md`. Include an example request or response in the PR. Current cross-service questions are listed in the [contract review](docs/CONTRACT_REVIEW.md).

## Review and merge

1. Request review from a colleague who owns a component affected by the change. For cross-service changes, include the affected consuming component owner and state which boundary they should review. Add another reviewer when another component is affected. For internal changes owned by a single author, select a colleague with the closest relevant expertise for an independent check. Author self-checks prepare the PR for review.
2. The reviewer follows the scenario in the PR description and comments on specific lines. Mark blocking findings with `[blocker]`, including the input, consequence, and expected behavior. Mark optional improvements with `[nit]`.
3. Use **Request changes** for blocking findings. The author fixes them, explains verification, and requests another review. Use **Approve** when the change is ready. Optional suggestions may accompany approval.
4. After at least one independent **Approve**, agreement on any changed shared contract from the affected owners, resolved review threads, and successful applicable checks, the author selects **Squash and merge**. Use the PR title as the squash commit title. New reviewable changes dismiss approvals and require another review.

Example findings for a map-based place filter follow.

- `[blocker]` For `bbox=20,49,21,50`, a point at longitude 20.5 and latitude 49.5 is missing from the response. Check coordinate order when building the envelope and add a regression case.
- `[nit]` Naming this parameter `minLon` would help match it to the coordinate order in the contract.
