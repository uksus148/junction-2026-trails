package io.junction.trails.places.web;

import com.fasterxml.jackson.databind.JsonNode;
import io.junction.trails.places.application.PlaceService;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpEntity;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.images.builder.ImageFromDockerfile;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@Testcontainers
@AutoConfigureMockMvc
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "spring.config.import=")
class PlaceApiTest {
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
    MockMvc browser;

    @Autowired
    JdbcClient jdbc;

    @MockitoSpyBean
    PlaceService places;

    @BeforeEach
    void seedPlaces() {
        jdbc.sql("TRUNCATE route_places, routes, places").update();
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

    @Test
    void createsAPlaceAndFindsItThroughSpatialSearch() {
        var response = http.postForEntity("/api/places", Map.of(
                "name", "  Skok waterfall  ", "lat", 49.1536, "lon", 20.0417,
                "tags", new String[]{" waterfall ", "nature", "waterfall"}), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        JsonNode created = response.getBody();
        assertThat(created.size()).isEqualTo(7);
        UUID id = UUID.fromString(created.get("id").asText());
        assertThat(created.get("name").asText()).isEqualTo("Skok waterfall");
        assertThat(created.get("lat").asDouble()).isEqualTo(49.1536);
        assertThat(created.get("lon").asDouble()).isEqualTo(20.0417);
        assertThat(created.get("tags").toString()).isEqualTo("[\"waterfall\",\"nature\"]");
        assertThat(created.get("photos").toString()).isEqualTo("[]");
        assertThat(created.get("source").asText()).isEqualTo("manual");
        assertThat(jdbc.sql("SELECT ST_SRID(geom) FROM places WHERE id = :id")
                .param("id", id).query(Integer.class).single()).isEqualTo(4326);

        var found = http.getForEntity("/api/places?bbox=20.03,49.15,20.05,49.16&tags=waterfall", JsonNode.class);
        assertThat(found.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(found.getBody().size()).isEqualTo(1);
        assertThat(found.getBody().get(0)).isEqualTo(created);
    }

    @Test
    void acceptsEmptyTagsAndCoordinateLimits() {
        var response = http.postForEntity("/api/places", Map.of(
                "name", "Boundary", "lat", -90, "lon", 180, "tags", new String[]{}), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        var found = http.getForEntity("/api/places?bbox=179,-90,180,-89", JsonNode.class);
        assertThat(found.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(found.getBody().get(0)).isEqualTo(response.getBody());
    }

    @Test
    void retainsTheFirstResearchedPlaceAndItsSourceOnReplay() {
        var first = http.postForEntity("/api/places", researched("node", 42, "https://example.org/original"), JsonNode.class);
        assertThat(first.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        JsonNode original = first.getBody();
        assertThat(original.size()).isEqualTo(7);
        assertThat(original.get("source").asText()).isEqualTo("https://example.org/original");
        var replay = new java.util.HashMap<String, Object>(researched("node", 42, "https://example.org/new-source"));
        replay.put("name", "Different name");
        replay.put("lat", 50.0);
        replay.put("tags", List.of("castle"));
        var second = http.postForEntity("/api/places", replay, JsonNode.class);
        assertThat(second.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(second.getBody()).isEqualTo(original);
        assertThat(jdbc.sql("SELECT count(*) FROM places WHERE osm_type='node' AND osm_id=42")
                .query(Integer.class).single()).isEqualTo(1);
        var found = http.getForEntity("/api/places?bbox=20,49,21,50&tags=researched", JsonNode.class);
        assertThat(found.getBody().get(0)).isEqualTo(original);
    }

    @Test
    void keepsOsmTypesDistinctAndManualRequestsIndependent() {
        var ids = new java.util.HashSet<String>();
        for (String type : List.of("node", "way", "relation")) {
            var response = http.postForEntity("/api/places", researched(type, 42, "https://example.org/source"), JsonNode.class);
            assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
            ids.add(response.getBody().get("id").asText());
        }
        assertThat(ids).hasSize(3);
        var manual = Map.of("name", "Manual", "lat", 49, "lon", 20, "tags", List.of());
        var first = http.postForEntity("/api/places", manual, JsonNode.class);
        var second = http.postForEntity("/api/places", manual, JsonNode.class);
        assertThat(first.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(second.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(first.getBody().get("id")).isNotEqualTo(second.getBody().get("id"));
    }

    @ParameterizedTest
    @ValueSource(booleans = {true, false})
    void waitsForConcurrentIngestionAndSeesItsCommitOrRollback(boolean commitWinner) throws Exception {
        UUID winnerId = UUID.randomUUID();
        try (var winner = DriverManager.getConnection(DATABASE.getJdbcUrl(), DATABASE.getUsername(), DATABASE.getPassword());
             var worker = Executors.newSingleThreadExecutor()) {
            winner.setAutoCommit(false);
            try {
                try (var insert = winner.prepareStatement("""
                        INSERT INTO places(id,name,geom,tags,source,osm_type,osm_id)
                        VALUES (?,'Concurrent winner',ST_SetSRID(ST_MakePoint(20.2,49.2),4326),
                            ARRAY['researched'],'https://example.org/winner','node',42)
                        """)) {
                    insert.setObject(1, winnerId);
                    insert.executeUpdate();
                }
                var pending = worker.submit(() -> http.postForEntity("/api/places",
                        researched("node", 42, "https://example.org/contender"), JsonNode.class));
                await().atMost(Duration.ofSeconds(10)).until(() -> jdbc.sql("""
                        SELECT count(*) FROM pg_stat_activity
                        WHERE datname=current_database() AND wait_event_type='Lock'
                            AND query LIKE '%INSERT INTO places%'
                        """).query(Integer.class).single() > 0);
                assertThat(pending.isDone()).isFalse();
                if (commitWinner) {
                    winner.commit();
                } else {
                    winner.rollback();
                }
                var response = pending.get(10, TimeUnit.SECONDS);
                assertThat(response.getStatusCode()).isEqualTo(commitWinner ? HttpStatus.OK : HttpStatus.CREATED);
                assertThat(response.getBody().get("source").asText()).isEqualTo(commitWinner
                        ? "https://example.org/winner" : "https://example.org/contender");
                if (commitWinner) {
                    assertThat(response.getBody().get("id").asText()).isEqualTo(winnerId.toString());
                }
                assertThat(jdbc.sql("SELECT count(*) FROM places WHERE osm_type='node' AND osm_id=42")
                        .query(Integer.class).single()).isEqualTo(1);
            } finally {
                winner.rollback();
            }
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"null", "{}", "[]", "true",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\"}",
            "{\"sourceUrl\":null,\"osmType\":\"node\",\"osmId\":42}",
            "{\"sourceUrl\":\"file:///etc/passwd\",\"osmType\":\"node\",\"osmId\":42}",
            "{\"sourceUrl\":\"https://user:password@example.org/\",\"osmType\":\"node\",\"osmId\":42}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"other\",\"osmId\":42}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\",\"osmId\":0}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\",\"osmId\":-1}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\",\"osmId\":1.5}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\",\"osmId\":\"42\"}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\",\"osmId\":9223372036854775808}",
            "{\"sourceUrl\":\"https://example.org\",\"osmType\":\"node\",\"osmId\":42,\"extra\":true}"
    })
    void rejectsIncompleteOrMalformedProvenanceWithoutWrites(String provenance) {
        assertInvalidPost("{\"name\":\"Place\",\"lat\":49,\"lon\":20,\"tags\":[],\"provenance\":" + provenance + "}");
    }

    @ParameterizedTest
    @ValueSource(strings = {"source", "unexpected"})
    void rejectsUnknownTopLevelFields(String field) {
        assertInvalidPost("{\"name\":\"Place\",\"lat\":49,\"lon\":20,\"tags\":[],\"" + field + "\":\"untrusted\"}");
    }

    @Test
    void mapsCreationStorageFailureWithoutLeakingInternalDetails() {
        doThrow(new CannotCreateTransactionException("private connection and credentials"))
                .when(places).create(any(), any());
        var response = http.postForEntity("/api/places", researched("node", 42, "https://example.org"), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(response.getBody().get("code").asText()).isEqualTo("storage_unavailable");
        assertThat(response.getBody().toString()).doesNotContain("private connection", "credentials");
        assertThat(jdbc.sql("SELECT count(*) FROM places").query(Integer.class).single()).isEqualTo(5);
    }

    @ParameterizedTest
    @CsvSource(value = {"node,null", "null,1", "other,1", "node,0", "node,-1"}, nullValues = "null")
    void databaseConstraintsRejectPartialOrInvalidOsmIdentity(String type, Long osmId) {
        assertThatThrownBy(() -> jdbc.sql("""
                UPDATE places SET osm_type=:type, osm_id=:osmId
                WHERE id='00000000-0000-0000-0000-000000000001'
                """).param("type", type, java.sql.Types.VARCHAR).param("osmId", osmId, java.sql.Types.BIGINT).update())
                .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
    }

    private void assertInvalidPost(String body) {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        var response = http.postForEntity("/api/places", new HttpEntity<>(body, headers), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody().get("code").asText()).isEqualTo("invalid_request");
        assertThat(response.getBody().get("detail").asText()).isNotBlank();
        assertThat(jdbc.sql("SELECT count(*) FROM places").query(Integer.class).single()).isEqualTo(5);
    }

    private static Map<String, Object> researched(String type, long osmId, String source) {
        return Map.of("name", "  Research place  ", "lat", 49.3, "lon", 20.3, "tags", List.of("researched"),
                "provenance", Map.of("sourceUrl", source, "osmType", type, "osmId", osmId));
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "{}", "null", "{", "{\"name\":\"\",\"lat\":49,\"lon\":20,\"tags\":[]}",
            "{\"name\":\"  \",\"lat\":49,\"lon\":20,\"tags\":[]}",
            "{\"lat\":49,\"lon\":20,\"tags\":[]}",
            "{\"name\":\"Place\",\"lon\":20,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":49,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":null,\"lon\":20,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":91,\"lon\":20,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":49,\"lon\":-181,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":1e999,\"lon\":20,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":\"bad\",\"lon\":20,\"tags\":[]}",
            "{\"name\":\"Place\",\"lat\":49,\"lon\":20}",
            "{\"name\":\"Place\",\"lat\":49,\"lon\":20,\"tags\":null}",
            "{\"name\":\"Place\",\"lat\":49,\"lon\":20,\"tags\":[\"\"]}",
            "{\"name\":\"Place\",\"lat\":49,\"lon\":20,\"tags\":[null]}",
            "{\"name\":\"Place\",\"lat\":49,\"lon\":20,\"tags\":[\"nature\",\"  \"]}"
    })
    void rejectsInvalidCreationWithoutWritingToTheDatabase(String json) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        var response = http.postForEntity("/api/places", new HttpEntity<>(json, headers), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.APPLICATION_PROBLEM_JSON);
        assertThat(response.getBody().get("detail").asText()).isNotBlank();
        assertThat(jdbc.sql("SELECT count(*) FROM places").query(Integer.class).single()).isEqualTo(5);
    }

    @Test
    void keepsUnexpectedIllegalArgumentsAsServerErrors() {
        doThrow(new IllegalArgumentException("internal implementation details"))
                .when(places).search(any(), anyList());
        var response = http.getForEntity("/api/places?bbox=20,49,21,50", String.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(response.getBody()).doesNotContain("internal implementation details");
    }

    @ParameterizedTest
    @ValueSource(strings = {"GET", "POST"})
    void allowsFrontendPreflightForJsonRequests(String method) throws Exception {
        browser.perform(options("/api/places")
                        .header(HttpHeaders.ORIGIN, "http://localhost:5173")
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, method)
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "Content-Type"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:5173"))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, "GET,POST"))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, "Content-Type"));
    }

    @Test
    void letsFrontendReadPlaceSearchResponses() throws Exception {
        browser.perform(get("/api/places").param("bbox", "20,49,21,50")
                        .header(HttpHeaders.ORIGIN, "http://localhost:5173"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:5173"));
    }

    @Test
    void letsFrontendReadValidationErrors() throws Exception {
        browser.perform(get("/api/places").param("bbox", "21,49,20,50")
                        .header(HttpHeaders.ORIGIN, "http://localhost:5173"))
                .andExpect(status().isBadRequest())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:5173"));
    }

    @Test
    void rejectsRequestsFromUnconfiguredOrigins() throws Exception {
        browser.perform(get("/api/places").param("bbox", "20,49,21,50")
                        .header(HttpHeaders.ORIGIN, "https://untrusted.example.org"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
    }

    @Test
    void rejectsPreflightForUnconfiguredMethods() throws Exception {
        browser.perform(options("/api/places")
                        .header(HttpHeaders.ORIGIN, "http://localhost:5173")
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "DELETE"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
    }
}
