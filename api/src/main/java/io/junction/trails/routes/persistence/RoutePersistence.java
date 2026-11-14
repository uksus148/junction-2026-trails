package io.junction.trails.routes.persistence;

import io.junction.trails.places.application.PlaceMapper;
import io.junction.trails.places.model.Place;
import io.junction.trails.places.persistence.PlaceEntity;
import io.junction.trails.places.persistence.PlaceRepository;
import io.junction.trails.routes.model.NewRoute;
import io.junction.trails.routes.model.Route;
import io.junction.trails.routes.model.RouteException;
import io.junction.trails.routes.model.RouteTrack;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class RoutePersistence {
    private final RouteRepository routes;
    private final PlaceRepository places;

    public List<Place> resolveStops(List<UUID> ids) {
        return orderedEntities(ids).stream().map(PlaceMapper::toPlace).toList();
    }

    @Transactional
    public Route save(NewRoute request, RouteTrack track) {
        return toRoute(routes.save(new RouteEntity(request, track, orderedEntities(request.placeIds()))));
    }

    public Route get(UUID id) {
        return toRoute(routes.findById(id).orElseThrow(() -> new RouteException(
                RouteException.Reason.ROUTE_NOT_FOUND, "The saved route does not exist.")));
    }

    private List<PlaceEntity> orderedEntities(List<UUID> ids) {
        Map<UUID, PlaceEntity> byId = places.findAllById(ids).stream()
                .collect(Collectors.toMap(PlaceEntity::getId, Function.identity()));
        return ids.stream().map(id -> {
            PlaceEntity place = byId.get(id);
            if (place == null) {
                throw new RouteException(RouteException.Reason.UNKNOWN_PLACE, "A referenced place does not exist.");
            }
            return place;
        }).toList();
    }

    private static Route toRoute(RouteEntity entity) {
        var coordinates = entity.getPoints().stream().map(point -> List.of(point.lon(), point.lat())).toList();
        return new Route(entity.getId(), new Route.Geometry("LineString", coordinates), entity.getDistanceKm(),
                entity.getAscentM(), entity.getDurationMin(),
                entity.getPlaces().stream().map(PlaceMapper::toPlace).toList(), List.of());
    }
}
