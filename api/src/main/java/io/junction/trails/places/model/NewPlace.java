package io.junction.trails.places.model;

import java.util.List;

public record NewPlace(String name, double lat, double lon, List<String> tags) {
    public NewPlace {
        if (name == null || name.isBlank()) {
            throw new InvalidPlaceInputException("name must not be blank");
        }
        if (!Double.isFinite(lat) || !Double.isFinite(lon)
                || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
            throw new InvalidPlaceInputException("lat and lon must be finite WGS84 coordinates");
        }
        if (tags == null || tags.stream().anyMatch(tag -> tag == null || tag.isBlank())) {
            throw new InvalidPlaceInputException("tags must be an array of non-empty values");
        }
        name = name.strip();
        tags = tags.stream().map(String::strip).distinct().toList();
    }
}
