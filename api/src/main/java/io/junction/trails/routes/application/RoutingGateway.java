package io.junction.trails.routes.application;

import io.junction.trails.routes.model.RouteTrack;
import io.junction.trails.routes.model.RoutingQuery;

public interface RoutingGateway {
    RouteTrack route(RoutingQuery query);
}
