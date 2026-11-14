package io.junction.trails.places.application;

import io.junction.trails.places.model.BoundingBox;
import io.junction.trails.places.model.NewPlace;
import io.junction.trails.places.model.Place;
import io.junction.trails.places.persistence.PlaceEntity;
import io.junction.trails.places.persistence.PlaceRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class PlaceService {
    private final PlaceRepository places;

    public List<Place> search(BoundingBox bounds, List<String> tags) {
        List<PlaceEntity> matches = tags.isEmpty()
                ? places.findWithinBounds(bounds.minLon(), bounds.minLat(), bounds.maxLon(), bounds.maxLat())
                : places.findWithinBoundsAndTags(bounds.minLon(), bounds.minLat(), bounds.maxLon(), bounds.maxLat(),
                        tags.toArray(String[]::new));
        return matches.stream().map(PlaceService::toPlace).toList();
    }

    @Transactional
    public Place create(NewPlace place) {
        return toPlace(places.save(new PlaceEntity(place, "manual")));
    }

    private static Place toPlace(PlaceEntity entity) {
        return new Place(entity.getId(), entity.getName(), entity.getLat(), entity.getLon(),
                entity.getTags(), List.of(), entity.getSource());
    }
}
