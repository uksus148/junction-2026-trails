# Optional route-availability research core

This implements Mukhamed's internal slice of the
[team plan](../docs/ROUTE_AVAILABILITY_RESEARCH_PLAN.md) after merged #54.
It is explicitly composed and invoked; `create_chat`, HTTP payloads, startup,
session records and the reply writer are unchanged. Murat selected optional consent,
planning dates and structured evidence on existing chat in the
[wire proposal](../docs/ROUTE_AVAILABILITY_CONTRACT.md); exact mapping and activation
still need the affected owners' agreement. No live
Groq/Exa acceptance or new automatic research is claimed.

## Inputs and gates

The caller supplies a **verified** `no_hiking_route` or `waypoint_not_routable`
result and the exact authoritative API Place records used in the failed route.
Outages, unknown UUIDs and other errors cannot enter this typed workflow.
Require explicit consent, a user-confirmed named section and jurisdiction; the
provider exposes no reliable failing-point index. Do not guess that section.

`extract_planning_dates` accepts an ISO day, month or inclusive range with an
explicit year: `2027-07-15`, `2027-07`, `2027-07-15/2027-07-20`. Invalid,
relative, free-form or yearless input such as "July" returns clarification.
This first slice asks for an unambiguous date expression instead of using another
model call or inferring a year from the event/history. Pass the current confirmed
expression on each changed plan; no history dates are silently reused. These
dates filter evidence, not ORS geometry.

Operator-reviewed `ResearchPolicy` provides exact official hostnames and a
publication/update age limit (1–365 days). There is no implicit trusted list or
accepted production freshness default. Never populate it from user/page/model
text. No policy, no consent, missing scope/dates or no remaining budget prevents
paid research. Add `www` separately if approved; subdomains are not implicitly trusted.

## Bounded research and validation

One fresh, domain-filtered Exa search returns at most three sources. It bypasses
the ordinary 24-hour place cache without reading, overwriting or clearing it.
This request-scoped exception avoids applying place-cache freshness to notices.
Notice searches request uncapped full text (`contents.text=true`, without
`maxCharacters`), as documented by [Exa](https://docs.exa.ai/reference/contents-retrieval).
Internal `textComplete` provenance requires that mode and, when supplied, one
successful provider content status. Capped, cached or unknown coverage stays
unconfirmed regardless of text length. Oversized pages remain incomplete markers;
the workflow rejects incomplete sources or more than 10,000 total characters before
assessment, without slicing or dropping a possible exception/revocation.
This records the provider's full-text contract, not an independent audit of opaque
provider omissions. Provenance is excluded from normal place-cache/prompt serialization.
One selected-provider tool call extracts at most three notices; it reuses Groq
`openai/gpt-oss-20b` or the selected Anthropic transport. All work, including quota
waits, fits the smaller of the caller's remaining deadline and the internal budget
(20 seconds by default, at most 60). There are no retries, source-page fetches,
routing calls, background jobs or writes.

Validation requires approved hosts, credential-free standard-port URLs, verbatim
excerpts, matching section/jurisdiction, publication date and applicability interval.
All evidence dates must appear literally as ISO dates in their respective excerpts;
natural-language/annual rules without explicit dates stay unconfirmed in this slice.
Freshness requires a source-parsed English `Published`, `Publication date`, `Updated`
or `Last modified` fact at a line/sentence boundary. The publication excerpt must
include that labelled ISO date; an applicability date cannot substitute for it.
Unsupported publication formats/roles remain unconfirmed.
A recent fetch alone does not make an old publication fresh. Truncated, missing,
stale or future-dated evidence, invented quotes/indices/fields and conflicting
overlapping notices stay unconfirmed. Model extraction still needs semantic/live
evaluation; these checks do not certify legal access, safety or exhaustive coverage.

Each finding retains the original URL, quote, publication date, retrieval time,
full applicability period and its intersection with the requested dates.
Missing applicable restrictions never means "open". The technical routing code
is preserved separately and `routingCause` is always `unconfirmed`; evidence cannot
establish why ORS failed. Optional failures preserve that result without private
errors; caller cancellation propagates.

## Internal use

```python
from gopstop_agent.availability import create_availability_research
from gopstop_agent.availability_models import AvailabilityRequest, ResearchPolicy

# canonical_places are the actual ApiPlace objects used in the failed request.
research = create_availability_research(
    http, cache, settings,
    ResearchPolicy(trustedHosts=("tanap.sk", "www.tanap.sk"), maxSourceAgeDays=30),
    tool_model=shared_tool_model,
)
result = await research.investigate(
    AvailabilityRequest(
        routingCode="waypoint_not_routable", places=canonical_places, optedIn=True,
        section="Rysy", jurisdiction="Slovakia", planningText="2027-07",
    ),
    remaining_seconds=remaining_chat_seconds,
)
```

The sample policy is an integration-review example, not an enabled runtime choice.
Results are internal facts, not a new wire response. Chat integration must validate/
clarify dates before ingestion, then invoke research only for a verified failure.
Review mapping the proposed planningWindow into this core, carrying authoritative
visits/confirmed scope, rendering sources/dates, localizing questions and preserving
the existing session-save step. The core
supplies no routeId and does not retry an earlier route POST. UI/date fields and
SQL/Kafka remain separate.
