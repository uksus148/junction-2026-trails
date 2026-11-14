package io.junction.trails.routes.application;

import io.junction.trails.routes.model.RouteTrack;
import io.junction.trails.routes.model.RoutingQuery;
import java.util.Optional;

public interface RouteTrackCache {
    Optional<RouteTrack> get(RoutingQuery query);

    void put(RoutingQuery query, RouteTrack track);
}
