package io.junction.trails.places.model;

import java.util.Arrays;

public record BoundingBox(double minLon, double minLat, double maxLon, double maxLat) {
    private static final String INVALID_BBOX =
            "bbox must contain minLon,minLat,maxLon,maxLat with finite WGS84 coordinates and increasing bounds";

    public static BoundingBox parse(String value) {
        String[] parts = value.split(",", -1);
        if (parts.length != 4) {
            throw new IllegalArgumentException(INVALID_BBOX);
        }
        double[] coordinates;
        try {
            coordinates = Arrays.stream(parts).mapToDouble(Double::parseDouble).toArray();
        } catch (NumberFormatException exception) {
            throw new IllegalArgumentException(INVALID_BBOX);
        }
        double minLon = coordinates[0];
        double minLat = coordinates[1];
        double maxLon = coordinates[2];
        double maxLat = coordinates[3];
        if (!Arrays.stream(coordinates).allMatch(Double::isFinite)
                || minLon < -180 || maxLon > 180 || minLat < -90 || maxLat > 90
                || minLon >= maxLon || minLat >= maxLat) {
            throw new IllegalArgumentException(INVALID_BBOX);
        }
        return new BoundingBox(minLon, minLat, maxLon, maxLat);
    }
}
