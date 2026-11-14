package io.junction.trails.routes.web;

import io.junction.trails.routes.application.RouteService;
import io.junction.trails.routes.model.Route;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/routes")
@RequiredArgsConstructor
class RouteController {
    private final RouteService routes;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    Route create(@RequestBody CreateRouteRequest request) {
        return routes.create(request.toCommand());
    }

    @GetMapping("/{id}")
    Route get(@PathVariable UUID id) {
        return routes.get(id);
    }
}
