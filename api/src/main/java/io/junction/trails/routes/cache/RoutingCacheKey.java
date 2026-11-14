package io.junction.trails.routes.cache;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.junction.trails.routes.model.RoutingQuery;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
public class RoutingCacheKey {
    public static final String PREFIX = "trego:routes:ors:v1:";

    private final ObjectMapper json;
    private final String providerEndpoint;

    public String forQuery(RoutingQuery query) {
        try {
            // v1 also identifies foot-hiking, elevation=true, instructions=false and metre units.
            byte[] input = json.writeValueAsBytes(List.of(providerEndpoint, query));
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(input);
            return PREFIX + HexFormat.of().formatHex(hash);
        } catch (JsonProcessingException | NoSuchAlgorithmException exception) {
            throw new IllegalStateException("Cannot encode the routing cache key", exception);
        }
    }
}
