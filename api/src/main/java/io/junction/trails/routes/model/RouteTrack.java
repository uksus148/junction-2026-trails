package io.junction.trails.routes.model;

import java.util.List;

public record RouteTrack(List<GeoPoint> points, double distanceKm, double ascentM, double durationMin) {
    public RouteTrack {
        points = List.copyOf(points);
        if (points.size() < 2 || !validMetric(distanceKm) || !validMetric(ascentM) || !validMetric(durationMin)) {
            throw new IllegalArgumentException("A route needs a LineString and finite non-negative metrics");
        }
    }

    private static boolean validMetric(double value) {
        return Double.isFinite(value) && value >= 0;
    }
}
