package io.junction.trails.routes.integration;

import com.fasterxml.jackson.databind.JsonNode;
import io.junction.trails.routes.application.RoutingGateway;
import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.RouteException;
import io.junction.trails.routes.model.RouteTrack;
import io.junction.trails.routes.model.RoutingQuery;
import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@RequiredArgsConstructor
public class OrsRoutingGateway implements RoutingGateway {
    private final RestClient client;
    private final OrsProperties properties;

    @Override
    public RouteTrack route(RoutingQuery query) {
        if (properties.apiKey().isBlank()) {
            throw providerError();
        }
        var coordinates = query.orderedWaypoints().stream().map(point -> List.of(point.lon(), point.lat())).toList();
        long started = System.nanoTime();
        try {
            JsonNode response = client.post().uri(properties.directionsUrl()).contentType(MediaType.APPLICATION_JSON)
                    .accept(MediaType.parseMediaType("application/geo+json"), MediaType.APPLICATION_JSON)
                    .body(Map.of("coordinates", coordinates, "elevation", true, "instructions", false, "units", "m"))
                    .retrieve().body(JsonNode.class);
            RouteTrack track = parse(response);
            if (deadlineExceeded(started)) {
                throw timeout();
            }
            return track;
        } catch (ResourceAccessException exception) {
            if (exception.contains(HttpTimeoutException.class) || exception.contains(SocketTimeoutException.class)
                    || deadlineExceeded(started)) {
                throw timeout();
            }
            throw providerError();
        } catch (RestClientResponseException exception) {
            if (deadlineExceeded(started)) {
                throw timeout();
            }
            if (isNoRoute(exception)) {
                throw new RouteException(RouteException.Reason.NO_HIKING_ROUTE,
                        "No walking route connects the requested waypoints.");
            }
            throw providerError();
        } catch (RestClientException exception) {
            if (deadlineExceeded(started)) {
                throw timeout();
            }
            throw providerError();
        } catch (IllegalArgumentException exception) {
            throw providerError();
        }
    }

    private boolean deadlineExceeded(long started) {
        return System.nanoTime() - started >= properties.readTimeout().toNanos();
    }

    private static RouteException timeout() {
        return new RouteException(RouteException.Reason.ROUTING_TIMEOUT, "Routing exceeded its deadline.");
    }

    private static RouteTrack parse(JsonNode response) {
        if (response == null || !"FeatureCollection".equals(response.path("type").asText())
                || !response.path("features").isArray() || response.path("features").size() != 1) {
            throw providerError();
        }
        JsonNode feature = response.path("features").get(0);
        JsonNode geometry = feature.path("geometry");
        if (!"Feature".equals(feature.path("type").asText())
                || !"LineString".equals(geometry.path("type").asText())
                || !geometry.path("coordinates").isArray()) {
            throw providerError();
        }
        var points = new ArrayList<GeoPoint>();
        for (JsonNode point : geometry.path("coordinates")) {
            if (!point.isArray() || point.size() < 2 || point.size() > 3) {
                throw providerError();
            }
            if (point.size() == 3) {
                finiteNumber(point.get(2));
            }
            points.add(new GeoPoint(finiteNumber(point.get(1)), finiteNumber(point.get(0))));
        }
        JsonNode properties = feature.path("properties");
        JsonNode summary = properties.path("summary");
        JsonNode ascent = summary.has("ascent") ? summary.get("ascent") : properties.get("ascent");
        return new RouteTrack(points, finiteNumber(summary.get("distance")) / 1000,
                finiteNumber(ascent), finiteNumber(summary.get("duration")) / 60);
    }

    private static double finiteNumber(JsonNode value) {
        if (value == null || !value.isNumber() || !Double.isFinite(value.doubleValue())) {
            throw providerError();
        }
        return value.doubleValue();
    }

    private static boolean isNoRoute(RestClientResponseException exception) {
        int status = exception.getStatusCode().value();
        if (status != 400 && status != 404) {
            return false;
        }
        try {
            JsonNode body = exception.getResponseBodyAs(JsonNode.class);
            JsonNode code = body == null ? null : body.path("error").path("code");
            return code != null && code.isIntegralNumber() && (code.intValue() == 2009 || code.intValue() == 2010);
        } catch (RestClientException exceptionReadingBody) {
            return false;
        }
    }

    private static RouteException providerError() {
        return new RouteException(RouteException.Reason.ROUTING_PROVIDER_ERROR,
                "Routing provider failed or returned invalid data.");
    }
}
