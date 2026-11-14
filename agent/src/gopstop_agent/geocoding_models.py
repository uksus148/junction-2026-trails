"""Validated OSM identity and WGS84 coordinates shared by search and selection."""

from typing import Literal

from pydantic import BaseModel, Field


class GeocodedPlace(BaseModel):
    osm_type: Literal["node", "way", "relation"]
    osm_id: int = Field(gt=0)
    display_name: str = Field(min_length=1, max_length=2000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/{self.osm_type}/{self.osm_id}"
