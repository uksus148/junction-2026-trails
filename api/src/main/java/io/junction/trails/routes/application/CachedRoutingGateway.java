package io.junction.trails.routes.application;

import io.junction.trails.routes.model.RouteTrack;
import io.junction.trails.routes.model.RoutingQuery;
import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
public class CachedRoutingGateway implements RoutingGateway {
    private final RoutingGateway provider;
    private final RouteTrackCache cache;

    @Override
    public RouteTrack route(RoutingQuery query) {
        var cached = cache.get(query);
        if (cached.isPresent()) {
            return cached.get();
        }
        var track = provider.route(query);
        cache.put(query, track);
        return track;
    }
}
