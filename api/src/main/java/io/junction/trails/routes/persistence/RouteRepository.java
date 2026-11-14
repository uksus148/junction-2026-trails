package io.junction.trails.routes.persistence;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RouteRepository extends JpaRepository<RouteEntity, UUID> {
    @Override
    @EntityGraph(attributePaths = "places")
    Optional<RouteEntity> findById(UUID id);
}
