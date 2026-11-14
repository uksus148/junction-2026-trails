package io.junction.trails.places.application;

import io.junction.trails.places.model.Place;
import io.junction.trails.places.persistence.PlaceEntity;
import java.util.List;
import lombok.AccessLevel;
import lombok.NoArgsConstructor;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public final class PlaceMapper {
    public static Place toPlace(PlaceEntity entity) {
        return new Place(entity.getId(), entity.getName(), entity.getLat(), entity.getLon(),
                entity.getTags(), List.of(), entity.getSource());
    }
}
