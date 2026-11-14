package io.junction.trails.routes.model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class NewRouteTest {
    @ParameterizedTest
    @CsvSource({"NaN,20", "49,Infinity", "-91,20", "91,20", "49,-181", "49,181"})
    void enforcesCoordinatesAtConstruction(double lat, double lon) {
        assertThatThrownBy(() -> new GeoPoint(lat, lon)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void preservesVisitsAndDescriptivePreferencesAsImmutableSnapshots() {
        UUID id = UUID.randomUUID();
        var visits = new ArrayList<>(List.of(id, id));
        var preferences = new ArrayList<>(List.of(" wild scenery ", " wild scenery "));
        var route = new NewRoute(new GeoPoint(49, 20), new GeoPoint(50, 21), visits, preferences);
        visits.clear();
        preferences.clear();
        assertThat(route.placeIds()).containsExactly(id, id);
        assertThat(route.preferences()).containsExactly(" wild scenery ", " wild scenery ");
        assertThatThrownBy(() -> route.placeIds().clear()).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void rejectsTooManyOrNullStops() {
        assertInvalid(Collections.nCopies(6, UUID.randomUUID()), List.of());
        assertInvalid(Collections.singletonList(null), List.of());
        assertInvalid(null, List.of());
        assertInvalid(List.of(), null);
        assertInvalid(List.of(), Collections.singletonList(null));
    }

    private static void assertInvalid(List<UUID> ids, List<String> preferences) {
        assertThatThrownBy(() -> new NewRoute(new GeoPoint(49, 20), new GeoPoint(50, 21), ids, preferences))
                .isInstanceOf(RouteException.class);
    }
}
