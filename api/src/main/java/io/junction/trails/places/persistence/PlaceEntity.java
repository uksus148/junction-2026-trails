package io.junction.trails.places.persistence;

import io.junction.trails.places.model.NewPlace;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.List;
import java.util.UUID;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.PrecisionModel;

@Entity
@Table(name = "places")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PlaceEntity {
    private static final GeometryFactory WGS84 = new GeometryFactory(new PrecisionModel(), 4326);

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Getter
    private UUID id;

    @Column(nullable = false, columnDefinition = "text")
    @Getter
    private String name;

    @Column(name = "geom", nullable = false, columnDefinition = "geometry(Point,4326)")
    private Point location;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(nullable = false, columnDefinition = "text[]")
    private String[] tags;

    @Column(nullable = false, columnDefinition = "text")
    @Getter
    private String source;

    @Column(name = "osm_type", columnDefinition = "text")
    @Getter
    private String osmType;

    @Column(name = "osm_id")
    @Getter
    private Long osmId;

    public PlaceEntity(NewPlace place, String source) {
        if (source == null || source.isBlank()) {
            throw new IllegalArgumentException("source must not be blank");
        }
        this.name = place.name();
        this.location = WGS84.createPoint(new Coordinate(place.lon(), place.lat()));
        this.tags = place.tags().toArray(String[]::new);
        this.source = source;
    }

    public double getLat() {
        return location.getY();
    }

    public double getLon() {
        return location.getX();
    }

    public List<String> getTags() {
        return List.of(tags);
    }
}
