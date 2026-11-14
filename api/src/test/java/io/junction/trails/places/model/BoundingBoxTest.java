package io.junction.trails.places.model;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BoundingBoxTest {
    @ParameterizedTest
    @CsvSource({"NaN,49,21,50", "20,NaN,21,50", "20,49,Infinity,50", "20,49,21,-Infinity",
            "-181,49,21,50", "20,-91,21,50", "20,49,181,50", "20,49,21,91",
            "21,49,20,50", "20,50,21,49", "20,49,20,50", "20,49,21,49"})
    void rejectsInvalidBoundsInTheConstructor(double minLon, double minLat, double maxLon, double maxLat) {
        assertThatThrownBy(() -> new BoundingBox(minLon, minLat, maxLon, maxLat))
                .isInstanceOf(InvalidPlaceInputException.class).hasMessageContaining("bbox");
    }

    @Test
    void acceptsWorldBounds() {
        assertThat(BoundingBox.parse("-180,-90,180,90"))
                .isEqualTo(new BoundingBox(-180, -90, 180, 90));
    }
}
