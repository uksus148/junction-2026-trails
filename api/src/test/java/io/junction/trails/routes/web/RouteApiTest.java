package io.junction.trails.routes.web;

import com.fasterxml.jackson.databind.JsonNode;
import io.junction.trails.routes.application.RoutingGateway;
import io.junction.trails.routes.persistence.RoutePersistence;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.images.builder.ImageFromDockerfile;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;

@Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = "spring.config.import=")
class RouteApiTest {
    private static final String FIRST = "00000000-0000-0000-0000-000000000001";
    private static final String SECOND = "00000000-0000-0000-0000-000000000002";
    private static final StubRoutingServer ORS;

    static {
        try {
            ORS = new StubRoutingServer();
        } catch (IOException exception) {
            throw new ExceptionInInitializerError(exception);
        }
    }

    @Container
    static final PostgreSQLContainer<?> DATABASE = new PostgreSQLContainer<>(
            DockerImageName.parse(new ImageFromDockerfile()
                    .withFileFromPath("Dockerfile", Path.of("../infra/postgres/Dockerfile"))
                    .withFileFromPath("init-extensions.sql", Path.of("../infra/postgres/init-extensions.sql"))
                    .get()).asCompatibleSubstituteFor("postgres"));

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry properties) {
        properties.add("spring.datasource.url", DATABASE::getJdbcUrl);
        properties.add("spring.datasource.username", DATABASE::getUsername);
        properties.add("spring.datasource.password", DATABASE::getPassword);
        properties.add("routing.ors.base-url", ORS::baseUrl);
        properties.add("routing.ors.api-key", () -> "fixture-key");
        properties.add("routing.ors.read-timeout", () -> "1s");
    }

    @Autowired
    TestRestTemplate http;
    @Autowired
    JdbcClient jdbc;
    @MockitoSpyBean
    RoutingGateway routing;
    @MockitoSpyBean
    RoutePersistence persistence;

    @BeforeEach
    void seed() throws IOException {
        ORS.reset();
        jdbc.sql("TRUNCATE route_places, routes, places").update();
        jdbc.sql("""
                INSERT INTO places (id,name,geom,tags,source) VALUES
                ('00000000-0000-0000-0000-000000000001','First',
                    ST_SetSRID(ST_MakePoint(20.05,49.05),4326),ARRAY['waterfall'],'manual'),
                ('00000000-0000-0000-0000-000000000002','Second',
                    ST_SetSRID(ST_MakePoint(20.1,49.1),4326),ARRAY['peak'],'https://example.org/source')
                """).update();
    }

    @AfterAll
    static void closeServer() {
        ORS.close();
    }

    @Test
    void persistsTheProviderTrackAndOrderedRepeatedVisitsBeforeReturningSuccess() {
        doAnswer(call -> {
            assertThat(TransactionSynchronizationManager.isActualTransactionActive()).isFalse();
            return call.callRealMethod();
        }).when(routing).route(anyList());
        var response = create(List.of(SECOND, FIRST, SECOND));
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        JsonNode route = response.getBody();
        assertThat(route.size()).isEqualTo(7);
        UUID id = UUID.fromString(route.get("id").asText());
        assertThat(route.get("geojson").get("type").asText()).isEqualTo("LineString");
        assertThat(route.get("geojson").get("coordinates").toString())
                .isEqualTo("[[20.0,49.0],[20.1,49.1],[20.2,49.2]]");
        assertThat(route.get("distanceKm").asDouble()).isEqualTo(7.5);
        assertThat(route.get("ascentM").asDouble()).isEqualTo(600);
        assertThat(route.get("durationMin").asDouble()).isEqualTo(90);
        assertThat(route.get("segments").toString()).isEqualTo("[]");
        assertThat(route.get("places").get(0).get("id").asText()).isEqualTo(SECOND);
        assertThat(route.get("places").get(1).get("id").asText()).isEqualTo(FIRST);
        assertThat(route.get("places").get(2).get("id").asText()).isEqualTo(SECOND);
        assertThat(route.get("places").get(0).get("source").asText()).isEqualTo("https://example.org/source");
        assertThat(jdbc.sql("SELECT place_id FROM route_places WHERE route_id=:id ORDER BY position")
                .param("id", id).query(UUID.class).list())
                .containsExactly(UUID.fromString(SECOND), UUID.fromString(FIRST), UUID.fromString(SECOND));
        assertThat(jdbc.sql("SELECT ST_SRID(geom) FROM routes WHERE id=:id")
                .param("id", id).query(Integer.class).single()).isEqualTo(4326);
        assertThat(jdbc.sql("SELECT array_to_json(preferences)::text FROM routes WHERE id=:id").param("id", id)
                .query(String.class).single()).isEqualTo("[\"wild scenery\"]");
        assertThat(ORS.getRequests()).hasSize(1);
        var sent = ORS.getRequests().get(0);
        assertThat(sent.method()).isEqualTo("POST");
        assertThat(sent.authorization()).isEqualTo("fixture-key");
        assertThat(sent.body().get("coordinates").toString())
                .isEqualTo("[[20.0,49.0],[20.1,49.1],[20.05,49.05],[20.1,49.1],[20.2,49.2]]");
        assertThat(sent.body().has("preferences")).isFalse();

        ORS.respond(503, "{}", 0);
        var saved = http.getForEntity("/api/routes/" + id, JsonNode.class);
        assertThat(saved.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(saved.getBody()).isEqualTo(route);
        assertThat(ORS.getRequests()).hasSize(1);
    }

    @Test
    void buildsADirectHikeAndRepeatedPostsCreateSeparateSavedRoutes() {
        var first = create(List.of());
        var second = create(List.of());
        assertThat(first.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(second.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(first.getBody().get("places").toString()).isEqualTo("[]");
        assertThat(first.getBody().get("id")).isNotEqualTo(second.getBody().get("id"));
        assertThat(ORS.getRequests()).hasSize(2);
        assertThat(routeCount()).isEqualTo(2);
    }

    @Test
    void routesThroughAPlaceCreatedByTheManualHttpEndpoint() {
        var place = http.postForEntity("/api/places", Map.of("name", "New viewpoint", "lat", 49.07,
                "lon", 20.08, "tags", List.of("viewpoint")), JsonNode.class);
        assertThat(place.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        String placeId = place.getBody().get("id").asText();
        var route = create(List.of(placeId));
        assertThat(route.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(route.getBody().get("places").get(0)).isEqualTo(place.getBody());
        var saved = http.getForEntity("/api/routes/" + route.getBody().get("id").asText(), JsonNode.class);
        assertThat(saved.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(saved.getBody()).isEqualTo(route.getBody());
        assertThat(ORS.getRequests().get(0).body().get("coordinates").get(1).toString())
                .isEqualTo("[20.08,49.07]");
    }

    @Test
    void resolvesEveryUuidBeforeCallingTheProvider() {
        var response = create(List.of(FIRST, UUID.randomUUID().toString()));
        assertProblem(response.getStatusCode(), response.getBody(), 422, "unknown_place");
        assertThat(ORS.getRequests()).isEmpty();
        assertThat(routeCount()).isZero();
    }

    @Test
    void rejectsTooManyStopsBeforeCallingTheProvider() {
        var response = create(java.util.Collections.nCopies(6, FIRST));
        assertProblem(response.getStatusCode(), response.getBody(), 400, "invalid_request");
        assertThat(ORS.getRequests()).isEmpty();
        assertThat(routeCount()).isZero();
    }

    @Test
    void returnsNoHikingRouteForAnExplicitProviderResultWithoutSaving() {
        ORS.respond(404, "{\"error\":{\"code\":2009}}", 0);
        var response = create(List.of());
        assertProblem(response.getStatusCode(), response.getBody(), 422, "no_hiking_route");
        assertThat(ORS.getRequests()).hasSize(1);
        assertThat(routeCount()).isZero();
    }

    @ParameterizedTest
    @ValueSource(ints = {401, 429, 500, 503})
    void doesNotRetryOrPersistProviderFailures(int status) {
        ORS.respond(status, "{\"error\":{\"message\":\"fixture-key internal body\"}}", 0);
        var response = create(List.of());
        assertProblem(response.getStatusCode(), response.getBody(), 502, "routing_provider_error");
        assertThat(response.getBody().toString()).doesNotContain("fixture-key", "internal body");
        assertThat(ORS.getRequests()).hasSize(1);
        assertThat(routeCount()).isZero();
    }

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void enforcesTheRealHttpReadTimeout(boolean headersFirst) {
        if (headersFirst) {
            ORS.delayBody(2500);
        } else {
            ORS.respond(200, "{}", 2500);
        }
        var response = create(List.of());
        assertProblem(response.getStatusCode(), response.getBody(), 504, "routing_timeout");
        assertThat(routeCount()).isZero();
        assertThat(ORS.getRequests()).hasSize(1);
    }

    @Test
    void doesNotReturnATransientSuccessWhenPersistenceFails() {
        doThrow(new CannotCreateTransactionException("fixture database outage"))
                .when(persistence).save(any(), any());
        var response = create(List.of());
        assertProblem(response.getStatusCode(), response.getBody(), 503, "storage_unavailable");
        assertThat(routeCount()).isZero();
        assertThat(ORS.getRequests()).hasSize(1);
    }

    @Test
    void distinguishesMissingRoutesFromMalformedIdentifiers() {
        var missing = http.getForEntity("/api/routes/" + UUID.randomUUID(), JsonNode.class);
        assertProblem(missing.getStatusCode(), missing.getBody(), 404, "route_not_found");
        var malformed = http.getForEntity("/api/routes/not-a-uuid", JsonNode.class);
        assertProblem(malformed.getStatusCode(), malformed.getBody(), 400, "invalid_request");
        assertThat(ORS.getRequests()).isEmpty();
    }

    @ParameterizedTest
    @ValueSource(strings = {"null", "{}", "{",
            "{\"start\":{},\"end\":{\"lat\":49,\"lon\":20},\"placeIds\":[],\"preferences\":[]}",
            "{\"start\":{\"lat\":91,\"lon\":20},\"end\":{\"lat\":49,\"lon\":20},\"placeIds\":[],\"preferences\":[]}",
            "{\"start\":{\"lat\":49,\"lon\":20},\"end\":{\"lat\":50,\"lon\":21},\"placeIds\":[\"bad\"],\"preferences\":[]}",
            "{\"start\":{\"lat\":49,\"lon\":20},\"end\":{\"lat\":50,\"lon\":21},\"placeIds\":[null],\"preferences\":[]}",
            "{\"start\":{\"lat\":49,\"lon\":20},\"end\":{\"lat\":50,\"lon\":21},\"placeIds\":[],\"preferences\":[null]}"
    })
    void rejectsMalformedRequestsWithoutCallingOrSaving(String json) {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        var response = http.postForEntity("/api/routes", new HttpEntity<>(json, headers), JsonNode.class);
        assertProblem(response.getStatusCode(), response.getBody(), 400, "invalid_request");
        assertThat(ORS.getRequests()).isEmpty();
        assertThat(routeCount()).isZero();
    }

    private org.springframework.http.ResponseEntity<JsonNode> create(List<String> ids) {
        return http.postForEntity("/api/routes", Map.of("start", Map.of("lat", 49.0, "lon", 20.0),
                "end", Map.of("lat", 49.2, "lon", 20.2), "placeIds", ids,
                "preferences", List.of("wild scenery")), JsonNode.class);
    }

    private long routeCount() {
        return jdbc.sql("SELECT count(*) FROM routes").query(Long.class).single();
    }

    private static void assertProblem(HttpStatusCode actual, JsonNode problem, int status, String code) {
        assertThat(actual.value()).isEqualTo(status);
        assertThat(problem.get("status").asInt()).isEqualTo(status);
        assertThat(problem.get("code").asText()).isEqualTo(code);
        assertThat(problem.get("detail").asText()).isNotBlank();
    }
}
