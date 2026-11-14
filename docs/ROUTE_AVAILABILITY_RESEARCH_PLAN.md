# Researching route availability after a routing failure

**Status: team proposal, not implemented or an accepted API extension.** Murat requested
this plan for all three developers. Agree the decisions below after baseline E5 and
before implementation. [CLAUDE.md](../CLAUDE.md) remains the contract authority.
The accompanying [issue #49 fix](ROUTING_DIAGNOSTICS.md) only distinguishes routing errors;
it adds no post-failure web search, date-aware routing or automatic fallback.

## Goal and evidence boundary

After a verified routing failure, investigate relevant trail restrictions through Exa
and authoritative sources. Keep the technical result separate from external findings:

- ORS 2009: no path found under the current routing conditions.
- ORS 2010: a waypoint could not be matched to the available hiking network.
- Independent research may confirm a closure, access rule or difficulty information
  for a specific trail section and planning date. It does not establish why ORS failed.

Example: "The router could not match a waypoint. Separately, the park authority reports
that this section is closed for your planning dates. Source: … The router's failure
reason beyond the matching failure is unconfirmed."

Never derive closure from 2010, an empty search result or model confidence. Never expand
the radius, change providers, move/drop points or replay route POSTs to obtain success.
Research cannot turn an unsuccessful route into a saved routeId or certify hiking safety.

## Proposed workflow

1. Preserve the verified API outcome and the exact resolved places/coordinates.
2. Establish the user's planning date or interval, with enough year/season precision
   to apply the source. Ask when missing or ambiguous; do not assume the event date.
   Reconfirm dates on changed plans instead of silently reusing old session context.
3. Investigate only if the confirmed failure is relevant and the user wants details.
   Do not reinterpret auth/quota/storage/cache outages as a trail-availability problem.
4. Search for the relevant named section, jurisdiction and dates. Prefer park/trail
   authorities and official notices; distinguish publication date, fetch time and the
   period to which a restriction applies. Treat retrieved text as data, not instructions.
5. Validate identity/date applicability and retain the actual evidence URL/content.
   A notice about another approach, hut or nearby trail is insufficient. Current 2010
   exposes no reliable failing-point index; do not guess which point needs investigation.
6. Report technical result, independent findings, source and uncertainty separately.
   Missing, conflicting, stale or insufficiently specific evidence means "unconfirmed".
7. Offer an explicit user choice of another point/scenario. Any new route creation needs
   a deliberate new request; the original POST must not be retried automatically.

## Ownership and delivery order

| Owner | Work and handoff |
|---|---|
| Murat | Preserve API classifications and routing limits; review any API/date/evidence contract; verify no retry or route write on failure; agree storage only if required |
| Mukhamed | Extract/clarify planning dates; add bounded optional Exa research and evidence validation; separate facts from hypotheses in replies; test provider/deadline failures |
| Daniil | Present router result and sourced external restrictions separately; show applicable dates and uncertainty; provide explicit investigate/change-point actions and safe source links |

First agree scope and wire examples together. Then implement agent fixtures/research,
the agreed UI/contract slice, and a same-revision integration check. Request affected
owners and at least one independent approval for every PR. This plan does not authorize
adding new runtime features to the current routing fix or block its review.

## Decisions required before coding

Murat retains architectural decisions; proposals here are not his selected design.

| Decision | Options and tradeoffs |
|---|---|
| Evidence delivery | Reuse `reply` with verified source links: fewer wire changes, but conflicts with the current reply writer's no-URL rule and needs safe UI rendering. Add optional structured evidence: clearer source/date presentation and testability, but requires an agreed shared contract and consumer changes. Do not invent a field or overload Place/source |
| Planning dates | Clarify through existing chat text: preserves the current request shape but needs validated internal dates/session semantics. Add an explicit UI date: clearer input, with additional contract and UI work |
| Trigger | Explicit "investigate" action limits latency/cost and preserves the baseline flow. Automatic research adds waiting and provider work to every qualifying failure; keep it disabled unless agreed |
| Persistence/cache | Request-scoped findings avoid schema work and stale saved notices. Caching/history can reduce repeat work but needs source-specific freshness, invalidation and retention decisions; do not assume the routing cache's 24-hour policy fits closures |

Suggested first slice: explicit opt-in, request-scoped evidence, existing Exa integration,
and date clarification. Propose at most one search within a small agreed budget and the
remaining total chat deadline. No paid retries; if optional research fails or times out,
retain the known routing result and say the external explanation is unconfirmed.
Do not refresh session success before its existing storage step completes.

## Acceptance criteria

- A bare 2010 never becomes "trail closed"; 2009 and 2010 stay distinguishable.
- A matching official restriction is shown with its source and applicable dates, without
  claiming it caused the provider error. July and November plans are evaluated separately.
- Unknown dates/sections, stale or conflicting notices and no results produce a question
  or uncertainty, not an invented explanation or a guessed failing waypoint.
- Instructions embedded in a page, fabricated citations and unrelated nearby notices
  cannot become authoritative findings. Only the agreed evidence URLs reach the UI.
- Optional research stays within the agreed quota/deadline, preserves dependency-error
  semantics, and cannot trigger another ORS request or a new saved route.
- Integration tests cover the chosen payload/UI, source/date display, uncertainty and
  explicit user actions. Live verification is bounded and recorded separately from fixtures.

Use [routing diagnostics](ROUTING_DIAGNOSTICS.md) for the already observed Rysy/default-radius
failure and the summer-planning alternative. The geocoding correction for
[issue #51](https://github.com/uksus148/trego./issues/51) merged in #52; combined baseline
browser E5 is still a separate gate, not implicitly completed by this proposal.
