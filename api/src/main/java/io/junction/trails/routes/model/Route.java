package io.junction.trails.routes.model;

import io.junction.trails.places.model.Place;
import java.util.List;
import java.util.UUID;

public record Route(UUID id, Geometry geojson, double distanceKm, double ascentM, double durationMin,
                    List<Place> places, List<Segment> segments) {
    public Route {
        places = List.copyOf(places);
        segments = List.copyOf(segments);
    }

    public record Geometry(String type, List<List<Double>> coordinates) {
        public Geometry {
            if (!"LineString".equals(type) || coordinates.size() < 2) {
                throw new IllegalArgumentException("Route geometry must be a LineString");
            }
            coordinates = coordinates.stream().map(List::copyOf).toList();
        }
    }

    public record Segment(double fromKm, double toKm, List<Place.Photo> photos) {
        public Segment {
            photos = List.copyOf(photos);
        }
    }
}
