package io.junction.trails.routes.cache;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.RouteException;
import io.junction.trails.routes.model.RouteTrack;
import io.junction.trails.routes.model.RoutingQuery;
import java.util.List;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ValkeyRouteTrackCacheTest {
    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void mapsReadAndWriteTransportFailuresToSafeCacheErrors(boolean write) {
        var client = mock(StringRedisTemplate.class);
        @SuppressWarnings("unchecked")
        ValueOperations<String, String> values = mock(ValueOperations.class);
        when(client.opsForValue()).thenReturn(values);
        var failure = new DataAccessResourceFailureException("fixture-password private.aivencloud.com");
        when(values.get(anyString())).thenThrow(failure);
        doThrow(failure).when(values).set(anyString(), anyString(), any(java.time.Duration.class));
        var json = new ObjectMapper();
        var cache = new ValkeyRouteTrackCache(client, json, new RoutingCacheKey(json, "https://ors.test"));
        var points = List.of(new GeoPoint(49, 20), new GeoPoint(50, 21));
        var query = new RoutingQuery(new NewRoute(points.getFirst(), points.getLast(), List.of(), List.of()), points);
        assertThatThrownBy(() -> {
            if (write) {
                cache.put(query, new RouteTrack(points, 1, 2, 3));
            } else {
                cache.get(query);
            }
        }).isInstanceOfSatisfying(RouteException.class, exception -> {
            assertThat(exception.getReason()).isEqualTo(RouteException.Reason.CACHE_UNAVAILABLE);
            assertThat(exception.getMessage()).doesNotContain("fixture-password", "aivencloud");
        });
    }
}
