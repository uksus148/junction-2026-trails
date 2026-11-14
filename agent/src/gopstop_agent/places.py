"""The agreed frontend Place and Photo response shapes."""

from pydantic import BaseModel, Field, HttpUrl


class Photo(BaseModel):
    url: HttpUrl
    thumbUrl: HttpUrl
    author: str
    license: str
    sourceUrl: HttpUrl
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Place(BaseModel):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tags: list[str]
    photos: list[Photo] = Field(default_factory=list)
    source: HttpUrl
