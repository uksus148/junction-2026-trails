# Routing failures and the Tatras demo

Prepared for issue [#49](https://github.com/uksus148/trego./issues/49) on
`fix/routing-waypoint-errors`, based on main `e2ba213`. Murat requested the error
distinction and authorized a demo correction. The API extension and revised demo
await affected-owner review; this is not completed E5 acceptance.

## Preserve the routing conditions

Keep the configured ORS endpoint and `foot-hiking`, ordered coordinates,
`elevation=true`, `instructions=false`, and metre units. Do not increase or disable
the snapping radius, relax difficulty/access filters, change providers, drop stops,
replace a waypoint or automatically replay the POST to obtain success.
This fix changes no request body, timeout, cache key or provider option.

The [ORS error reference](https://giscience.github.io/openrouteservice/v9.10.0/api-reference/error-codes)
distinguishes these numeric results on HTTP 400/404:

| ORS code | API HTTP/code | Confirmed meaning |
|---|---|---|
| 2009 | 422 `no_hiking_route` | No route found between the locations under the current conditions |
| 2010 | 422 `waypoint_not_routable` | A waypoint could not be matched to the available hiking network within the provider search radius |

Unknown, malformed, non-integral or overflowing codes remain provider errors.
Authentication, quota, outages and timeouts are not reclassified. Match structured
numeric codes, not English provider messages; never expose provider bodies.
Neither result establishes a closure, season, difficulty exclusion or bad coordinate
as its cause. Do not identify a particular failed point without structured evidence.

The agent recognizes each complete 422 Problem Details response as its own typed result.
For an unmatched waypoint, it asks to check coordinates or choose another point, with
no routeId, substitution or radius retry. Earlier ingested places may remain. Unknown
or inconsistent problems remain dependency errors. The frontend retains the code and
displays the safe API detail without new UI fields.

## Bounded live verification

On November 14, 2026, two direct live ORS POSTs used exactly the existing options,
default radius and no automatic retries. Coordinate pairs are `[lon,lat]`, from Daniil's
reported Nominatim findings. No coordinate was moved to improve snapping. These
diagnostic requests made no PostgreSQL or Valkey writes.

| Case | Ordered coordinates | Result |
|---|---|---|
| Original Rysy via Skok | `[20.0636,49.1194]`, `[20.04527,49.15312]`, `[20.08846,49.17932]` | HTTP 404, ORS 2010; response identified coordinate 2 and 350 m radius |
| Revised Popradské pleso via Skok | `[20.0636,49.1194]`, `[20.04527,49.15312]`, `[20.0795,49.1532]` | HTTP 200; 14,752.2 m, 17,360.7 s, 741.1 m ascent; 607 geometry points; waypoint indices 0/218/606 |

The first confirms a failed network match, not why the graph excluded it. The second
verifies topology through all three visits, not trail legality, current conditions or
the full browser workflow. Never substitute Popradské pleso for a user-requested Rysy.

## Demo correction and planning season

Use this explicit **summer planning** candidate for the next E5 run:

> Plan a summer hike in July from Štrbské Pleso to Popradské pleso via the Skok waterfall. I love wild scenery.

Keep the original Rysy request as an unmatched-waypoint regression. Merely changing its
requested season does not make a missing graph match routable.

Independent seasonal evidence: TANAP's
[October 30, 2026 notice](https://www.tanap.sk/od-1-novembra-sa-v-tatranskom-narodnom-parku-zacina-sezonna-uzavera-9441/)
confirms the November 1–May 31 closure period for selected trails. Its
[visitor regulations](https://www.tanap.sk/wp-content/uploads/navstevny_poriadok_tanapu.pdf)
list Chata pod Rysmi/Rysy, the Trigan–Popradské section, and the section above Skok
in Annex 3A (printed pages 18–19). The revised demo plans July, not a November walk.

The MVP has no date/season field or seasonal-closure engine. A successful ORS track
does not guarantee safety/open access or prove that the provider used the July context.
Calendar-aware routing is not implemented by this wording change.

Daniil should align the visible demo suggestion after agreement; existing frontend
mock fixtures remain mock-only and were not rewritten here. Mukhamed owns the separate
Nominatim query/ambiguity issue [#51](https://github.com/uksus148/trego./issues/51), which
can still prevent chat from reaching the now-distinct routing outcomes.


## Regression evidence

Local `mvn --batch-mode --no-transfer-progress verify` passed 194 API tests with zero
failures/errors/skips on JDK 25 targeting Java 21. Tests distinguish 2009/2010, reject
unknown/coerced/overflowing codes, retain server failures, assert exact provider options,
and check no retry, cache entry or route write after a matching failure. The initial
full run exposed an incorrect expected `/ors` fixture prefix in the new test; corrected
that test and completed verification without changing production request URLs.

Agent fixtures passed 252 tests, including actual HTTP handoff -> typed matching failure
-> distinct reply facts/session recording without a route ID. The reply prompt prohibits
unconfirmed closure/season/difficulty causes; no live LLM run is claimed by these fixtures.
Frontend passed 31 tests and its production build under Node 24. Runtime frontend behavior
is unchanged; its existing API client retains the new code/detail. Dependency deprecation
and frontend chunk-size warnings remain non-blocking. No GitHub CI result is claimed for
this local unpublished branch. The summarized live evidence is in the ignored generated
`api/target/demo-routing-report.json`; no provider key is included.
