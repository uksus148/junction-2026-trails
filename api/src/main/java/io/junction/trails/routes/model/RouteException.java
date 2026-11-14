package io.junction.trails.routes.model;

import lombok.Getter;

@Getter
public class RouteException extends RuntimeException {
    private final Reason reason;

    public RouteException(Reason reason, String detail) {
        super(detail);
        this.reason = reason;
    }

    public enum Reason {
        INVALID_REQUEST, UNKNOWN_PLACE, NO_HIKING_ROUTE, ROUTING_PROVIDER_ERROR,
        STORAGE_UNAVAILABLE, ROUTING_TIMEOUT, ROUTE_NOT_FOUND
    }
}
