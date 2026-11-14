package io.junction.trails.routes.web;

import io.junction.trails.routes.model.RouteException;
import java.util.Locale;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.transaction.TransactionSystemException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice(assignableTypes = RouteController.class)
@Order(Ordered.HIGHEST_PRECEDENCE)
class RouteExceptionHandler {
    @ExceptionHandler(RouteException.class)
    ProblemDetail routeFailure(RouteException exception) {
        HttpStatus status = switch (exception.getReason()) {
            case INVALID_REQUEST -> HttpStatus.BAD_REQUEST;
            case UNKNOWN_PLACE, NO_HIKING_ROUTE, WAYPOINT_NOT_ROUTABLE -> HttpStatus.UNPROCESSABLE_ENTITY;
            case ROUTING_PROVIDER_ERROR -> HttpStatus.BAD_GATEWAY;
            case STORAGE_UNAVAILABLE, CACHE_UNAVAILABLE -> HttpStatus.SERVICE_UNAVAILABLE;
            case ROUTING_TIMEOUT -> HttpStatus.GATEWAY_TIMEOUT;
            case ROUTE_NOT_FOUND -> HttpStatus.NOT_FOUND;
        };
        return problem(status, exception.getReason().name().toLowerCase(Locale.ROOT), exception.getMessage());
    }

    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentTypeMismatchException.class})
    ProblemDetail invalidRequest(Exception exception) {
        return problem(HttpStatus.BAD_REQUEST, "invalid_request", "The route request contains invalid or missing fields.");
    }

    @ExceptionHandler({DataAccessResourceFailureException.class, CannotCreateTransactionException.class,
            TransactionSystemException.class})
    ProblemDetail storageUnavailable(Exception exception) {
        return problem(HttpStatus.SERVICE_UNAVAILABLE, "storage_unavailable", "Route storage is unavailable.");
    }

    private static ProblemDetail problem(HttpStatus status, String code, String detail) {
        var problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setProperty("code", code);
        return problem;
    }
}
