package io.junction.trails.places.model;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class NewPlaceTest {
    @ParameterizedTest
    @CsvSource({"NaN,20", "49,NaN", "Infinity,20", "49,-Infinity",
            "-91,20", "91,20", "49,-181", "49,181"})
    void rejectsInvalidCoordinates(double lat, double lon) {
        assertThatThrownBy(() -> new NewPlace("Place", lat, lon, List.of()))
                .isInstanceOf(InvalidPlaceInputException.class);
    }

    @Test
    void normalizesValuesAndOwnsItsTagSnapshot() {
        var tags = new ArrayList<>(List.of(" waterfall ", "nature", "waterfall"));
        var place = new NewPlace("  Skok  ", 49, 20, tags);
        tags.clear();
        assertThat(place.name()).isEqualTo("Skok");
        assertThat(place.tags()).containsExactly("waterfall", "nature");
    }

    @Test
    void responseModelsOwnTheirCollectionSnapshots() {
        var tags = new ArrayList<>(List.of("waterfall"));
        var photos = new ArrayList<Place.Photo>();
        var place = new Place(UUID.randomUUID(), "Skok", 49, 20, tags, photos, "manual");
        tags.clear();
        photos.add(new Place.Photo("url", "thumb", "author", "license", "source", 49, 20));
        assertThat(place.tags()).containsExactly("waterfall");
        assertThat(place.photos()).isEmpty();
    }
}
