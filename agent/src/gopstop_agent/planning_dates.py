"""Explicit planning dates; never infer a year from the event or session history."""

import calendar
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class PlanningWindow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("Planning dates must be ordered.")
        return self


def extract_planning_dates(text: str) -> PlanningWindow | None:
    """Accept an ISO day/month/range; ask for clarification for other expressions."""
    text = text.strip()
    try:
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:\s*/\s*(\d{4}-\d{2}-\d{2}))?", text)
        if match:
            start = date.fromisoformat(match[1])
            return PlanningWindow(start=start, end=date.fromisoformat(match[2]) if match[2] else start)
        if re.fullmatch(r"\d{4}-\d{2}", text):
            year, month = map(int, text.split("-"))
            return PlanningWindow(start=date(year, month, 1),
                                  end=date(year, month, calendar.monthrange(year, month)[1]))
    except ValueError:
        pass
    return None
