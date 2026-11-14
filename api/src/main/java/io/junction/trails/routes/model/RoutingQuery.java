package io.junction.trails.routes.model;

import java.util.List;
import java.util.Objects;

public record RoutingQuery(NewRoute request, List<GeoPoint> orderedWaypoints) {
    public RoutingQuery {
        Objects.requireNonNull(request, "Route request is required");
        orderedWaypoints = List.copyOf(orderedWaypoints);
        if (orderedWaypoints.size() != request.placeIds().size() + 2
                || !orderedWaypoints.getFirst().equals(request.start())
                || !orderedWaypoints.getLast().equals(request.end())) {
            throw new IllegalArgumentException("Waypoints must match the requested endpoints and visit count");
        }
    }
}
