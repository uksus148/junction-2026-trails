package io.junction.trails.places.web;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.images.builder.ImageFromDockerfile;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import static org.assertj.core.api.Assertions.assertThat;

@Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "spring.config.import=")
class PlaceSearchTest {
    @Container
    static final PostgreSQLContainer<?> DATABASE = new PostgreSQLContainer<>(
            DockerImageName.parse(new ImageFromDockerfile()
                    .withFileFromPath("Dockerfile", Path.of("../infra/postgres/Dockerfile"))
                    .withFileFromPath("init-extensions.sql", Path.of("../infra/postgres/init-extensions.sql"))
                    .get()).asCompatibleSubstituteFor("postgres"));

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry properties) {
        properties.add("spring.datasource.url", DATABASE::getJdbcUrl);
        properties.add("spring.datasource.username", DATABASE::getUsername);
        properties.add("spring.datasource.password", DATABASE::getPassword);
    }

    @Autowired
    TestRestTemplate http;

    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void seedPlaces() {
        jdbc.sql("TRUNCATE places").update();
        jdbc.sql("""
                INSERT INTO places (id, name, geom, tags, source) VALUES
                ('00000000-0000-0000-0000-000000000001', 'Inside waterfall',
                    ST_SetSRID(ST_MakePoint(20.5, 49.5), 4326), ARRAY['waterfall', 'nature'], 'fixture'),
                ('00000000-0000-0000-0000-000000000002', 'Inside castle',
                    ST_SetSRID(ST_MakePoint(20.6, 49.6), 4326), ARRAY['castle'], 'fixture'),
                ('00000000-0000-0000-0000-000000000003', 'Outside waterfall',
                    ST_SetSRID(ST_MakePoint(22, 51), 4326), ARRAY['waterfall'], 'fixture'),
                ('00000000-0000-0000-0000-000000000004', 'Boundary waterfall',
                    ST_SetSRID(ST_MakePoint(20, 49), 4326), ARRAY['waterfall'], 'fixture'),
                ('00000000-0000-0000-0000-000000000005', 'Reversed coordinates',
                    ST_SetSRID(ST_MakePoint(49.5, 20.5), 4326), ARRAY['waterfall'], 'fixture')
                """).update();
    }

    @Test
    void filtersByBoundingBoxAndReturnsTheContractShape() {
        var response = http.getForEntity("/api/places?bbox=20,49,21,50", JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        JsonNode places = response.getBody();
        assertThat(places.size()).isEqualTo(3);
        JsonNode first = places.get(0);
        assertThat(first.size()).isEqualTo(7);
        assertThat(first.get("id").asText()).isEqualTo("00000000-0000-0000-0000-000000000001");
        assertThat(first.get("name").asText()).isEqualTo("Inside waterfall");
        assertThat(first.get("lat").asDouble()).isEqualTo(49.5);
        assertThat(first.get("lon").asDouble()).isEqualTo(20.5);
        assertThat(first.get("tags").toString()).isEqualTo("[\"waterfall\",\"nature\"]");
        assertThat(first.get("photos").isArray()).isTrue();
        assertThat(first.get("photos").size()).isZero();
        assertThat(first.get("source").asText()).isEqualTo("fixture");
        assertThat(places.get(2).get("name").asText()).isEqualTo("Boundary waterfall");
    }

    @Test
    void filtersByAnyRequestedTagAndTrimsWhitespace() {
        var response = http.getForEntity("/api/places?bbox=20,49,21,50&tags={tags}",
                JsonNode.class, "castle, nature");
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().size()).isEqualTo(2);
        assertThat(response.getBody().get(1).get("name").asText()).isEqualTo("Inside castle");
    }

    @Test
    void includesBoundaryPointsButExcludesOutsidePoints() {
        var response = http.getForEntity("/api/places?bbox=20,49,21,50&tags=waterfall", JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().size()).isEqualTo(2);
        assertThat(response.getBody().get(1).get("name").asText()).isEqualTo("Boundary waterfall");
    }

    @Test
    void returnsAnEmptyArrayWhenNothingMatches() {
        var response = http.getForEntity("/api/places?bbox=0,0,1,1", JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().toString()).isEqualTo("[]");
    }

    @Test
    void bindsTagValuesAsData() {
        var response = http.getForEntity("/api/places?bbox=20,49,21,50&tags={tags}",
                JsonNode.class, "castle') OR true --");
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().size()).isZero();
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "20,49,21", "20,49,21,50,51", "x,49,21,50", "NaN,49,21,50",
            "20,49,Infinity,50", "-181,49,21,50", "20,-91,21,50", "20,49,181,50",
            "20,49,21,91", "21,49,20,50", "20,50,21,49", "20,49,20,50"})
    void rejectsInvalidBoundsWithAnExplanation(String bbox) {
        var response = http.getForEntity("/api/places?bbox={bbox}", JsonNode.class, bbox);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody().get("detail").asText()).contains("bbox");
    }

    @Test
    void requiresBoundingBox() {
        assertThat(http.getForEntity("/api/places", JsonNode.class).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsEmptyTagEntries() {
        var response = http.getForEntity("/api/places?bbox=20,49,21,50&tags=castle,,waterfall", JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody().get("detail").asText()).contains("tags");
    }
}
