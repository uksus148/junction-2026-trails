package io.junction.trails.places.persistence;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PlaceRepository extends JpaRepository<PlaceEntity, UUID> {
    String WITHIN_BOUNDS = """
            SELECT p.id, p.name, p.geom, p.tags, p.source, p.osm_type, p.osm_id
            FROM places p
            WHERE ST_Covers(ST_MakeEnvelope(:minLon, :minLat, :maxLon, :maxLat, 4326), p.geom)
            """;

    Optional<PlaceEntity> findByOsmTypeAndOsmId(String osmType, long osmId);

    @Modifying
    @Query(value = """
            INSERT INTO places (id, name, geom, tags, source, osm_type, osm_id)
            VALUES (:id, :name, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:tags AS text[]),
                    :source, :osmType, :osmId)
            ON CONFLICT (osm_type, osm_id) DO NOTHING
            """, nativeQuery = true)
    int insertResearched(@Param("id") UUID id, @Param("name") String name,
                         @Param("lat") double lat, @Param("lon") double lon,
                         @Param("tags") String[] tags, @Param("source") String source,
                         @Param("osmType") String osmType, @Param("osmId") long osmId);

    @Query(value = WITHIN_BOUNDS + " ORDER BY p.id", nativeQuery = true)
    List<PlaceEntity> findWithinBounds(@Param("minLon") double minLon, @Param("minLat") double minLat,
                                      @Param("maxLon") double maxLon, @Param("maxLat") double maxLat);

    @Query(value = WITHIN_BOUNDS + " AND p.tags && CAST(:tags AS text[]) ORDER BY p.id",
            nativeQuery = true)
    List<PlaceEntity> findWithinBoundsAndTags(@Param("minLon") double minLon, @Param("minLat") double minLat,
                                             @Param("maxLon") double maxLon, @Param("maxLat") double maxLat,
                                             @Param("tags") String[] tags);
}
