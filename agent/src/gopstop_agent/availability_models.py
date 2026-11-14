"""Internal research inputs/results; these are not new HTTP chat fields."""

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from gopstop_agent.api_models import ApiPlace
from gopstop_agent.intent import Name
from gopstop_agent.planning_dates import PlanningWindow


RoutingFailure = Literal["no_hiking_route", "waypoint_not_routable"]
Effect = Literal["restriction", "restriction_lifted", "difficulty"]


class InternalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ResearchPolicy(InternalModel):
    # Operator-reviewed hosts/freshness, never values extracted from a user or page.
    trustedHosts: tuple[str, ...] = Field(default=(), max_length=8)
    maxSourceAgeDays: int = Field(ge=1, le=365)

    @field_validator("trustedHosts")
    @classmethod
    def validate_hosts(cls, hosts):
        for host in hosts:
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host) or "." not in host:
                raise ValueError("Use explicit lowercase official hostnames.")
            if HttpUrl("https://" + host).host != host or any(not part for part in host.split(".")):
                raise ValueError("Invalid official hostname.")
        return hosts


class AvailabilityRequest(InternalModel):
    # The caller supplies a verified typed routing failure and authoritative visits.
    routingCode: RoutingFailure
    places: list[ApiPlace] = Field(min_length=2, max_length=7)
    optedIn: bool = False
    planningText: str = Field(default="", max_length=300)
    section: Name | None = None
    jurisdiction: Name | None = None


class DraftNotice(InternalModel):
    sourceIndex: int = Field(ge=0, le=2)
    effect: Effect
    quote: str = Field(min_length=1, max_length=2000)
    publishedQuote: str = Field(min_length=1, max_length=500)
    publishedOn: date
    validFrom: date
    validTo: date


class Assessment(InternalModel):
    findings: list[DraftNotice] = Field(max_length=3)


class AvailabilityEvidence(InternalModel):
    sourceUrl: HttpUrl
    effect: Effect
    quote: str
    publishedQuote: str
    publishedOn: date
    validFrom: date
    validTo: date
    retrievedAt: datetime
    appliesDuring: PlanningWindow


class AvailabilityResult(InternalModel):
    routingCode: RoutingFailure
    status: Literal["not_requested", "clarification", "unconfirmed", "evidence_found"]
    planning: PlanningWindow | None = None
    section: Name | None = None
    question: str | None = None
    uncertainty: str | None = None
    findings: list[AvailabilityEvidence] = Field(default_factory=list)
    # External evidence never establishes the cause of the provider's failure.
    routingCause: Literal["unconfirmed"] = "unconfirmed"
