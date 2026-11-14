package io.junction.trails.routes.integration;

import java.net.URI;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "routing.ors")
public record OrsProperties(URI baseUrl, String apiKey, Duration connectTimeout, Duration readTimeout) {
    public OrsProperties {
        if (baseUrl == null || !("https".equals(baseUrl.getScheme()) || "http".equals(baseUrl.getScheme()))
                || baseUrl.getHost() == null || baseUrl.getUserInfo() != null
                || baseUrl.getQuery() != null || baseUrl.getFragment() != null) {
            throw new IllegalArgumentException("ORS base URL must be an HTTP(S) server URL");
        }
        if (connectTimeout == null || connectTimeout.isZero() || connectTimeout.isNegative()
                || readTimeout == null || readTimeout.isZero() || readTimeout.isNegative()) {
            throw new IllegalArgumentException("ORS timeouts must be positive");
        }
        apiKey = apiKey == null ? "" : apiKey;
    }

    public URI directionsUrl() {
        return URI.create(baseUrl.toString().replaceAll("/+$", "") + "/v2/directions/foot-hiking/geojson");
    }

    @Override
    public String toString() {
        return "OrsProperties[baseUrl=" + baseUrl + ", apiKey=<redacted>, connectTimeout="
                + connectTimeout + ", readTimeout=" + readTimeout + "]";
    }
}
