package io.junction.trails.places.web;

import io.junction.trails.places.model.InvalidPlaceInputException;
import io.junction.trails.places.model.NewPlace;
import java.util.List;

record CreatePlaceRequest(String name, Double lat, Double lon, List<String> tags) {
    NewPlace toCommand() {
        if (lat == null || lon == null) {
            throw new InvalidPlaceInputException("lat and lon are required");
        }
        return new NewPlace(name, lat, lon, tags);
    }
}
