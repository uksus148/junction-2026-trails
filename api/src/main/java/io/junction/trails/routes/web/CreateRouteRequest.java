package io.junction.trails.routes.web;

import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import java.util.List;
import java.util.UUID;

record CreateRouteRequest(Point start, Point end, List<UUID> placeIds, List<String> preferences) {
    NewRoute toCommand() {
        if (start == null || end == null) {
            throw NewRoute.invalid("start and end are required");
        }
        return new NewRoute(start.toPoint(), end.toPoint(), placeIds, preferences);
    }

    record Point(Double lat, Double lon) {
        GeoPoint toPoint() {
            if (lat == null || lon == null) {
                throw NewRoute.invalid("lat and lon are required for each endpoint");
            }
            try {
                return new GeoPoint(lat, lon);
            } catch (IllegalArgumentException exception) {
                throw NewRoute.invalid(exception.getMessage());
            }
        }
    }
}
