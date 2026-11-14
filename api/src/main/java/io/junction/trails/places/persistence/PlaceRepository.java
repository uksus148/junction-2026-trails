package io.junction.trails.places.persistence;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PlaceRepository extends JpaRepository<PlaceEntity, UUID> {
    String WITHIN_BOUNDS = """
            SELECT p.id, p.name, p.geom, p.tags, p.source
            FROM places p
            WHERE ST_Covers(ST_MakeEnvelope(:minLon, :minLat, :maxLon, :maxLat, 4326), p.geom)
            """;

    @Query(value = WITHIN_BOUNDS + " ORDER BY p.id", nativeQuery = true)
    List<PlaceEntity> findWithinBounds(@Param("minLon") double minLon, @Param("minLat") double minLat,
                                      @Param("maxLon") double maxLon, @Param("maxLat") double maxLat);

    @Query(value = WITHIN_BOUNDS + " AND p.tags && CAST(:tags AS text[]) ORDER BY p.id",
            nativeQuery = true)
    List<PlaceEntity> findWithinBoundsAndTags(@Param("minLon") double minLon, @Param("minLat") double minLat,
                                             @Param("maxLon") double maxLon, @Param("maxLat") double maxLat,
                                             @Param("tags") String[] tags);
}
