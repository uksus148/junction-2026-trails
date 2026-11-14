package io.junction.trails.routes.cache;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.RoutingQuery;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RoutingCacheKeyTest {
    private static final GeoPoint START = new GeoPoint(49, 20);
    private static final GeoPoint END = new GeoPoint(50, 21);
    private static final GeoPoint STOP = new GeoPoint(49.5, 20.5);
    private static final UUID FIRST = new UUID(0, 1);
    private static final UUID SECOND = new UUID(0, 2);
    private final RoutingCacheKey keys = new RoutingCacheKey(new ObjectMapper(), "https://ors.test/foot-hiking");

    @Test
    void hashesCompleteOrderedInputsWithoutExposingCoordinatesOrPreferences() {
        var original = query(List.of(FIRST, SECOND), List.of("wild scenery"), List.of(START, STOP, STOP, END));
        String key = keys.forQuery(original);
        assertThat(key).matches("trego:routes:ors:v1:[0-9a-f]{64}");
        assertThat(keys.forQuery(query(List.of(FIRST, SECOND), List.of("wild scenery"),
                List.of(START, STOP, STOP, END)))).isEqualTo(key);
        var changed = List.of(
                query(List.of(SECOND, FIRST), List.of("wild scenery"), List.of(START, STOP, STOP, END)),
                query(List.of(FIRST, FIRST), List.of("wild scenery"), List.of(START, STOP, STOP, END)),
                query(List.of(FIRST), List.of("wild scenery"), List.of(START, STOP, END)),
                query(List.of(FIRST, SECOND), List.of("quiet trails"), List.of(START, STOP, STOP, END)),
                query(List.of(FIRST, SECOND), List.of("wild scenery"), List.of(START, STOP, END, END)),
                query(List.of(FIRST, SECOND), List.of("wild scenery"), List.of(END, STOP, STOP, START)));
        assertThat(changed.stream().map(keys::forQuery).toList()).doesNotContain(key).doesNotHaveDuplicates();
        assertThat(new RoutingCacheKey(new ObjectMapper(), "https://other-provider.test/foot-hiking")
                .forQuery(original)).isNotEqualTo(key);
    }

    @Test
    void preferenceOrderAndBoundariesAreNotLostWhileEncodingTheKey() {
        var first = query(List.of(), List.of("a", "b"), List.of(START, END));
        assertThat(keys.forQuery(first)).isNotEqualTo(keys.forQuery(
                query(List.of(), List.of("b", "a"), List.of(START, END))));
        assertThat(keys.forQuery(first)).isNotEqualTo(keys.forQuery(
                query(List.of(), List.of("a,b"), List.of(START, END))));
    }

    @Test
    void snapshotsResolvedWaypointsAndRejectsInconsistentInternalQueries() {
        var points = new ArrayList<>(List.of(START, END));
        var snapshot = query(List.of(), List.of(), points);
        points.clear();
        assertThat(snapshot.orderedWaypoints()).containsExactly(START, END);
        assertThatThrownBy(() -> new RoutingQuery(snapshot.request(), List.of(END, START)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RoutingQuery(snapshot.request(), List.of(START, STOP, END)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static RoutingQuery query(List<UUID> ids, List<String> preferences, List<GeoPoint> points) {
        return new RoutingQuery(new NewRoute(points.getFirst(), points.getLast(), ids, preferences), points);
    }
}
