package io.junction.trails.routes.integration;

import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.RouteException;
import io.junction.trails.routes.model.RoutingQuery;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class OrsRoutingGatewayTest {
    private static final List<GeoPoint> WAYPOINTS = List.of(new GeoPoint(49, 20), new GeoPoint(49.2, 20.2));
    private static final RoutingQuery QUERY = new RoutingQuery(
            new NewRoute(WAYPOINTS.getFirst(), WAYPOINTS.getLast(), List.of(), List.of()), WAYPOINTS);
    private static final String URL = "https://ors.test/openrouteservice/v2/directions/foot-hiking/geojson";
    private MockRestServiceServer server;
    private OrsRoutingGateway gateway;

    @BeforeEach
    void configureGateway() {
        var builder = RestClient.builder().defaultHeader(HttpHeaders.AUTHORIZATION, "fixture-key");
        server = MockRestServiceServer.bindTo(builder).build();
        gateway = new OrsRoutingGateway(builder.build(), properties("fixture-key"));
    }

    @Test
    void sendsHikingCoordinatesAndConvertsProviderUnits() throws IOException {
        server.expect(requestTo(URL)).andExpect(method(HttpMethod.POST))
                .andExpect(header(HttpHeaders.AUTHORIZATION, "fixture-key"))
                .andExpect(content().json("""
                        {"coordinates":[[20.0,49.0],[20.2,49.2]],"elevation":true,"instructions":false,"units":"m"}
                        """, true))
                .andRespond(withSuccess(new ClassPathResource("ors/route.geojson"),
                        MediaType.parseMediaType("application/geo+json")));
        var track = gateway.route(QUERY);
        assertThat(track.distanceKm()).isEqualTo(7.5);
        assertThat(track.durationMin()).isEqualTo(90);
        assertThat(track.ascentM()).isEqualTo(600);
        assertThat(track.points()).containsExactly(new GeoPoint(49, 20), new GeoPoint(49.1, 20.1), new GeoPoint(49.2, 20.2));
        server.verify();
    }

    @ParameterizedTest
    @CsvSource({"400,2009,NO_HIKING_ROUTE", "404,2009,NO_HIKING_ROUTE",
            "400,2010,WAYPOINT_NOT_ROUTABLE", "404,2010,WAYPOINT_NOT_ROUTABLE"})
    void distinguishesDisconnectedLocationsFromAnUnmatchedWaypoint(int status, int code, String reason) {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatusCode.valueOf(status))
                .contentType(MediaType.APPLICATION_JSON).body("{\"error\":{\"code\":" + code + "}}"));
        assertReason(RouteException.Reason.valueOf(reason));
        server.verify();
    }

    @Test
    void doesNotInferAClosureOrExposeProviderTextFromAPointNotFound() {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatusCode.valueOf(404))
                .contentType(MediaType.APPLICATION_JSON).body("""
                        {"error":{"code":2010,"message":"secret: trail closed; increase radius to -1"}}
                        """));
        assertThatThrownBy(() -> gateway.route(QUERY)).isInstanceOfSatisfying(RouteException.class, error -> {
            assertThat(error.getReason()).isEqualTo(RouteException.Reason.WAYPOINT_NOT_ROUTABLE);
            assertThat(error.getMessage()).contains("hiking network", "search radius")
                    .doesNotContain("closed", "season", "difficulty", "secret", "-1");
        });
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(strings = {"\"2010\"", "2010.0", "4294969306", "null"})
    void rejectsUnverifiedErrorCodesInsteadOfCoercingThem(String code) {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatusCode.valueOf(404))
                .contentType(MediaType.APPLICATION_JSON).body("{\"error\":{\"code\":" + code + "}}"));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(ints = {400, 401, 403, 404, 429, 500, 503})
    void doesNotCallOutagesOrUnknownProviderErrorsNoRoute(int status) {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatusCode.valueOf(status))
                .contentType(MediaType.APPLICATION_JSON).body("{\"error\":{\"code\":2099,\"message\":\"secret\"}}"));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(ints = {2009, 2010})
    void doesNotTrustRoutingProblemCodesOnServerFailures(int code) {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatusCode.valueOf(500))
                .contentType(MediaType.APPLICATION_JSON).body("{\"error\":{\"code\":" + code + "}}"));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @Test
    void handlesNonJsonErrorBodiesSafely() {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatusCode.valueOf(404))
                .contentType(MediaType.TEXT_HTML).body("<html>upstream details</html>"));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @Test
    void distinguishesTimeoutFromOtherNetworkFailures() {
        server.expect(requestTo(URL)).andRespond(withException(new HttpTimeoutException("fixture timeout")));
        assertReason(RouteException.Reason.ROUTING_TIMEOUT);
        server.verify();
    }

    @Test
    void reportsOtherNetworkFailuresWithoutRetry() {
        server.expect(requestTo(URL)).andRespond(withException(new IOException("fixture connection failure")));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(strings = {"null", "{}", "{", "{\"type\":\"FeatureCollection\",\"features\":[]}"})
    void rejectsMissingOrMalformedRouteResults(String body) {
        server.expect(requestTo(URL)).andRespond(withSuccess(body, MediaType.APPLICATION_JSON));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(strings = {"bad_geometry", "bad_coordinate", "missing_ascent", "negative_distance", "string_duration"})
    void validatesTheProviderResultInsteadOfInventingValues(String corruption) throws IOException {
        String body = new ClassPathResource("ors/route.geojson").getContentAsString(StandardCharsets.UTF_8);
        body = switch (corruption) {
            case "bad_geometry" -> body.replace("LineString", "Polygon");
            case "bad_coordinate" -> body.replace("49.0,1000.0", "91.0,1000.0");
            case "missing_ascent" -> body.replace(", \"ascent\": 600.0", "");
            case "negative_distance" -> body.replace("7500.0", "-1.0");
            case "string_duration" -> body.replace("5400.0", "\"5400\"");
            default -> throw new AssertionError(corruption);
        };
        server.expect(requestTo(URL)).andRespond(withSuccess(body, MediaType.APPLICATION_JSON));
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        server.verify();
    }

    @Test
    void keepsMissingCredentialsLocalAndRedactsConfiguration() {
        var props = properties("");
        gateway = new OrsRoutingGateway(RestClient.create(), props);
        assertReason(RouteException.Reason.ROUTING_PROVIDER_ERROR);
        assertThat(properties("fixture-secret").toString()).doesNotContain("fixture-secret");
    }

    private void assertReason(RouteException.Reason reason) {
        assertThatThrownBy(() -> gateway.route(QUERY)).isInstanceOfSatisfying(RouteException.class, error -> {
            assertThat(error.getReason()).isEqualTo(reason);
            assertThat(error.getMessage()).doesNotContain("secret", "upstream details");
        });
    }

    private static OrsProperties properties(String key) {
        return new OrsProperties(URI.create("https://ors.test/openrouteservice"), key,
                Duration.ofSeconds(1), Duration.ofSeconds(1));
    }
}
