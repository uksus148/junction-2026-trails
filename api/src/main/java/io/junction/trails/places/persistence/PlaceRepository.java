package io.junction.trails.places.persistence;

import io.junction.trails.places.model.BoundingBox;
import io.junction.trails.places.model.Place;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class PlaceRepository {
    private final JdbcClient jdbc;

    public PlaceRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<Place> search(BoundingBox bounds, List<String> tags) {
        String sql = """
                SELECT id, name, ST_Y(geom) AS lat, ST_X(geom) AS lon, tags, source
                FROM places
                WHERE ST_Covers(ST_MakeEnvelope(:minLon, :minLat, :maxLon, :maxLat, 4326), geom)
                """;
        if (!tags.isEmpty()) {
            sql += " AND tags && ARRAY[:tags]::text[]";
        }
        var query = jdbc.sql(sql + " ORDER BY id")
                .param("minLon", bounds.minLon()).param("minLat", bounds.minLat())
                .param("maxLon", bounds.maxLon()).param("maxLat", bounds.maxLat());
        if (!tags.isEmpty()) {
            query = query.param("tags", tags);
        }
        return query.query((row, number) -> {
            var sqlTags = row.getArray("tags");
            try {
                return new Place(row.getObject("id", UUID.class), row.getString("name"),
                        row.getDouble("lat"), row.getDouble("lon"),
                        List.of((String[]) sqlTags.getArray()), List.of(), row.getString("source"));
            } finally {
                sqlTags.free();
            }
        }).list();
    }
}
