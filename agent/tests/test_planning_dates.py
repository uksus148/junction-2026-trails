from datetime import date

import pytest
from pydantic import ValidationError

from gopstop_agent.availability_models import AvailabilityRequest, ResearchPolicy
from gopstop_agent.planning_dates import extract_planning_dates
from test_trails_api import place


@pytest.mark.parametrize("text,start,end", [
    ("2027-07-15", date(2027, 7, 15), date(2027, 7, 15)),
    (" 2027-07-01 / 2027-07-05 ", date(2027, 7, 1), date(2027, 7, 5)),
    ("2028-02", date(2028, 2, 1), date(2028, 2, 29)),
])
def test_explicit_year_and_date_precision_are_preserved(text, start, end):
    result = extract_planning_dates(text)
    assert (result.start, result.end) == (start, end)


@pytest.mark.parametrize("text", ["", "July", "next summer", "июль", "07/08", "2027-02-29",
                                     "2027-13", "2027-07-05/2027-07-01", "2027-07-15 or 2027-08-01"])
def test_missing_ambiguous_or_invalid_dates_need_clarification(text):
    assert extract_planning_dates(text) is None


def test_only_verified_routing_outcomes_can_enter_optional_research():
    with pytest.raises(ValidationError):
        AvailabilityRequest(routingCode="routing_provider_error", places=[place(1), place(2)])
    for host in ("https://authority.example", "authority.example/path", "authority.example@evil.test", "*.example"):
        with pytest.raises(ValidationError):
            ResearchPolicy(trustedHosts=(host,), maxSourceAgeDays=30)
