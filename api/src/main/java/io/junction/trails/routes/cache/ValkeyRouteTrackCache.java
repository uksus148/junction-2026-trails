package io.junction.trails.routes.cache;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.junction.trails.routes.application.RouteTrackCache;
import io.junction.trails.routes.model.RouteException;
import io.junction.trails.routes.model.RouteTrack;
import io.junction.trails.routes.model.RoutingQuery;
import java.time.Duration;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;

@RequiredArgsConstructor
public class ValkeyRouteTrackCache implements RouteTrackCache {
    public static final Duration TTL = Duration.ofHours(24);

    private final StringRedisTemplate valkey;
    private final ObjectMapper json;
    private final RoutingCacheKey keys;

    @Override
    public Optional<RouteTrack> get(RoutingQuery query) {
        String key = keys.forQuery(query);
        try {
            String value = valkey.opsForValue().get(key);
            if (value == null) {
                return Optional.empty();
            }
            RouteTrack track = json.readerFor(RouteTrack.class)
                    .with(DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES,
                            DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES,
                            DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
                    .readValue(value);
            if (track == null) {
                throw unavailable();
            }
            return Optional.of(track);
        } catch (DataAccessException | JsonProcessingException exception) {
            throw unavailable();
        }
    }

    @Override
    public void put(RoutingQuery query, RouteTrack track) {
        String key = keys.forQuery(query);
        try {
            valkey.opsForValue().set(key, json.writeValueAsString(track), TTL);
        } catch (DataAccessException | JsonProcessingException exception) {
            throw unavailable();
        }
    }

    private static RouteException unavailable() {
        return new RouteException(RouteException.Reason.CACHE_UNAVAILABLE, "Routing cache is unavailable.");
    }
}
