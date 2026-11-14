package io.junction.trails.routes.application;

import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.Route;
import io.junction.trails.routes.persistence.RoutePersistence;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class RouteService {
    private final RoutingGateway routing;
    private final RoutePersistence persistence;

    public Route create(NewRoute request) {
        var stops = persistence.resolveStops(request.placeIds());
        var waypoints = new ArrayList<GeoPoint>();
        waypoints.add(request.start());
        stops.forEach(place -> waypoints.add(new GeoPoint(place.lat(), place.lon())));
        waypoints.add(request.end());
        var track = routing.route(List.copyOf(waypoints));
        return persistence.save(request, track);
    }

    public Route get(UUID id) {
        return persistence.get(id);
    }
}
