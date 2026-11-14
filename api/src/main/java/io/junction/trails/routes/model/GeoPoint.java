package io.junction.trails.routes.model;

public record GeoPoint(double lat, double lon) {
    public GeoPoint {
        if (!Double.isFinite(lat) || !Double.isFinite(lon)
                || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
            throw new IllegalArgumentException("Coordinates must be finite WGS84 values");
        }
    }
}
