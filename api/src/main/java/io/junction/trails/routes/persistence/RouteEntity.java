package io.junction.trails.routes.persistence;

import io.junction.trails.places.persistence.PlaceEntity;
import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.RouteTrack;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.PrecisionModel;

@Entity
@Table(name = "routes")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class RouteEntity {
    private static final GeometryFactory WGS84 = new GeometryFactory(new PrecisionModel(), 4326);

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Getter
    private UUID id;

    @Column(name = "geom", nullable = false, columnDefinition = "geometry(LineString,4326)")
    private LineString geometry;

    @Column(name = "start_geom", nullable = false, columnDefinition = "geometry(Point,4326)")
    private Point startGeom;

    @Column(name = "end_geom", nullable = false, columnDefinition = "geometry(Point,4326)")
    private Point endGeom;

    @Column(name = "distance_km", nullable = false)
    @Getter
    private double distanceKm;

    @Column(name = "ascent_m", nullable = false)
    @Getter
    private double ascentM;

    @Column(name = "duration_min", nullable = false)
    @Getter
    private double durationMin;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(nullable = false, columnDefinition = "text[]")
    private String[] preferences;

    @ManyToMany
    @JoinTable(name = "route_places", joinColumns = @JoinColumn(name = "route_id"),
            inverseJoinColumns = @JoinColumn(name = "place_id"))
    @OrderColumn(name = "position", nullable = false)
    private List<PlaceEntity> places;

    public RouteEntity(NewRoute request, RouteTrack track, List<PlaceEntity> places) {
        if (!places.stream().map(PlaceEntity::getId).toList().equals(request.placeIds())) {
            throw new IllegalArgumentException("Persisted route stops must match the requested visits");
        }
        geometry = WGS84.createLineString(track.points().stream().map(RouteEntity::coordinate).toArray(Coordinate[]::new));
        startGeom = WGS84.createPoint(coordinate(request.start()));
        endGeom = WGS84.createPoint(coordinate(request.end()));
        distanceKm = track.distanceKm();
        ascentM = track.ascentM();
        durationMin = track.durationMin();
        preferences = request.preferences().toArray(String[]::new);
        this.places = new ArrayList<>(places);
    }

    public List<GeoPoint> getPoints() {
        return Arrays.stream(geometry.getCoordinates()).map(point -> new GeoPoint(point.y, point.x)).toList();
    }

    public List<PlaceEntity> getPlaces() {
        return List.copyOf(places);
    }

    private static Coordinate coordinate(GeoPoint point) {
        return new Coordinate(point.lon(), point.lat());
    }
}
