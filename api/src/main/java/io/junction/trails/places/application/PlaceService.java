package io.junction.trails.places.application;

import io.junction.trails.places.model.BoundingBox;
import io.junction.trails.places.model.NewPlace;
import io.junction.trails.places.model.Place;
import io.junction.trails.places.model.ResearchProvenance;
import io.junction.trails.places.persistence.PlaceEntity;
import io.junction.trails.places.persistence.PlaceRepository;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.annotation.Isolation;

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
        return matches.stream().map(PlaceMapper::toPlace).toList();
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public PlaceCreation create(NewPlace place, ResearchProvenance provenance) {
        if (provenance == null) {
            return new PlaceCreation(PlaceMapper.toPlace(places.save(new PlaceEntity(place, "manual"))), true);
        }
        int inserted = places.insertResearched(UUID.randomUUID(), place.name(), place.lat(), place.lon(),
                place.tags().toArray(String[]::new), provenance.sourceUrl(), provenance.osmType(), provenance.osmId());
        // A new READ COMMITTED statement sees the winner after ON CONFLICT waited for its commit.
        var canonical = places.findByOsmTypeAndOsmId(provenance.osmType(), provenance.osmId())
                .orElseThrow(() -> new IllegalStateException("The canonical place disappeared during ingestion"));
        return new PlaceCreation(PlaceMapper.toPlace(canonical), inserted == 1);
    }
}
