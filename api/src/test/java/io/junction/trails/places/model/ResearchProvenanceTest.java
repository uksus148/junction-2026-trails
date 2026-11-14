package io.junction.trails.places.model;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ResearchProvenanceTest {
    @Test
    void retainsTheSelectedUrlAndSupportsThePositiveBigintBoundary() {
        var provenance = new ResearchProvenance("https://example.org/hike?source=research#view", "relation", Long.MAX_VALUE);
        assertThat(provenance.sourceUrl()).isEqualTo("https://example.org/hike?source=research#view");
        assertThat(provenance.osmId()).isEqualTo(Long.MAX_VALUE);
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"relative/path", "https:///missing-host", "ftp://example.org/hike",
            "https://user:secret@example.org/", "https://example.org:99999/", "https://example.org/a b"})
    void rejectsInvalidSourcesAtTheModelBoundary(String source) {
        assertThatThrownBy(() -> new ResearchProvenance(source, "node", 1))
                .isInstanceOf(InvalidPlaceInputException.class);
    }

    @Test
    void rejectsInvalidIdentitiesAtTheModelBoundary() {
        assertThatThrownBy(() -> new ResearchProvenance("https://example.org", "NODE", 1))
                .isInstanceOf(InvalidPlaceInputException.class);
        assertThatThrownBy(() -> new ResearchProvenance("https://example.org", "node", 0))
                .isInstanceOf(InvalidPlaceInputException.class);
    }
}
