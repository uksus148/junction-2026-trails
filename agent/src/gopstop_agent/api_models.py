"""Validate the agreed API wire shapes without exposing persistence entities."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Nonnegative = Annotated[float, Field(ge=0)]


class WireModel(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)


class ApiPhoto(WireModel):
    url: HttpUrl
    thumbUrl: HttpUrl
    author: Text
    license: Text
    sourceUrl: HttpUrl
    lat: Latitude
    lon: Longitude


class ApiPlace(WireModel):
    id: UUID
    name: Text
    lat: Latitude
    lon: Longitude
    tags: list[Text]
    photos: list[ApiPhoto]
    source: Text


class ApiLineString(WireModel):
    type: Literal["LineString"]
    coordinates: list[tuple[Longitude, Latitude]] = Field(min_length=2)


class ApiSegment(WireModel):
    fromKm: Nonnegative
    toKm: Nonnegative
    photos: list[ApiPhoto]

    @model_validator(mode="after")
    def check_order(self):
        if self.toKm < self.fromKm:
            raise ValueError("Segment distances must increase.")
        return self


class ApiRoute(WireModel):
    id: Text
    geojson: ApiLineString
    distanceKm: Nonnegative
    ascentM: Nonnegative
    durationMin: Nonnegative
    places: list[ApiPlace]
    segments: list[ApiSegment]


class ApiProblem(WireModel):
    type: Text
    title: Text
    status: int
    detail: Text
    code: Text
