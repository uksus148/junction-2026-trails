package io.junction.trails.routes.application;

import io.junction.trails.routes.model.GeoPoint;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.RouteException;
import io.junction.trails.routes.model.RoutingQuery;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

class CachedRoutingGatewayTest {
    @ParameterizedTest
    @EnumSource(value = RouteException.Reason.class, names = {"NO_HIKING_ROUTE", "ROUTING_TIMEOUT", "ROUTING_PROVIDER_ERROR"})
    void doesNotCacheOrRetryProviderFailures(RouteException.Reason reason) {
        var provider = mock(RoutingGateway.class);
        var cache = mock(RouteTrackCache.class);
        var gateway = new CachedRoutingGateway(provider, cache);
        var points = List.of(new GeoPoint(49, 20), new GeoPoint(50, 21));
        var query = new RoutingQuery(new NewRoute(points.getFirst(), points.getLast(), List.of(), List.of()), points);
        var failure = new RouteException(reason, "Fixture failure");
        when(cache.get(query)).thenReturn(Optional.empty());
        when(provider.route(query)).thenThrow(failure);
        assertThatThrownBy(() -> gateway.route(query)).isSameAs(failure);
        verify(cache).get(query);
        verify(provider).route(query);
        verifyNoMoreInteractions(cache, provider);
    }
}
