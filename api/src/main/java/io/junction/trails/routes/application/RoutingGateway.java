package io.junction.trails.routes.application;

import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.RouteTrack;
import java.util.List;

public interface RoutingGateway {
    RouteTrack route(List<GeoPoint> orderedWaypoints);
}
