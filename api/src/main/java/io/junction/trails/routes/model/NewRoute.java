package io.junction.trails.routes.model;

import java.util.List;
import java.util.UUID;

public record NewRoute(GeoPoint start, GeoPoint end, List<UUID> placeIds, List<String> preferences) {
    public static final int MAX_INTERMEDIATE_STOPS = 5;

    public NewRoute {
        if (start == null || end == null || placeIds == null || preferences == null) {
            throw invalid("start, end, placeIds, and preferences are required");
        }
        if (placeIds.size() > MAX_INTERMEDIATE_STOPS || placeIds.stream().anyMatch(value -> value == null)) {
            throw invalid("placeIds must contain at most five non-null UUIDs");
        }
        if (preferences.stream().anyMatch(value -> value == null)) {
            throw invalid("preferences must contain non-null strings");
        }
        placeIds = List.copyOf(placeIds);
        preferences = List.copyOf(preferences);
    }

    public static RouteException invalid(String detail) {
        return new RouteException(RouteException.Reason.INVALID_REQUEST, detail);
    }
}
