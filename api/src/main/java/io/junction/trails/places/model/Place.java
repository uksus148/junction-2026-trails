package io.junction.trails.places.model;

import java.util.List;
import java.util.UUID;

public record Place(UUID id, String name, double lat, double lon,
                    List<String> tags, List<Photo> photos, String source) {
    public Place {
        tags = List.copyOf(tags);
        photos = List.copyOf(photos);
    }

    public record Photo(String url, String thumbUrl, String author, String license,
                        String sourceUrl, double lat, double lon) {
    }
}
