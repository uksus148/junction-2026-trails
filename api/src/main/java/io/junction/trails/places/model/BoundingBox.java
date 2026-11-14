package io.junction.trails.places.model;

import java.util.Arrays;

public record BoundingBox(double minLon, double minLat, double maxLon, double maxLat) {
    private static final String INVALID_BBOX =
            "bbox must contain minLon,minLat,maxLon,maxLat with finite WGS84 coordinates and increasing bounds";

    public BoundingBox {
        if (!Double.isFinite(minLon) || !Double.isFinite(minLat)
                || !Double.isFinite(maxLon) || !Double.isFinite(maxLat)
                || minLon < -180 || maxLon > 180 || minLat < -90 || maxLat > 90
                || minLon >= maxLon || minLat >= maxLat) {
            throw new InvalidPlaceInputException(INVALID_BBOX);
        }
    }

    public static BoundingBox parse(String value) {
        if (value == null) {
            throw new InvalidPlaceInputException(INVALID_BBOX);
        }
        String[] parts = value.split(",", -1);
        if (parts.length != 4) {
            throw new InvalidPlaceInputException(INVALID_BBOX);
        }
        double[] coordinates;
        try {
            coordinates = Arrays.stream(parts).mapToDouble(Double::parseDouble).toArray();
        } catch (NumberFormatException exception) {
            throw new InvalidPlaceInputException(INVALID_BBOX);
        }
        return new BoundingBox(coordinates[0], coordinates[1], coordinates[2], coordinates[3]);
    }
}
