package io.junction.trails.places.web;

import io.junction.trails.places.model.InvalidPlaceInputException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.QueryTimeoutException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.transaction.TransactionSystemException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice(assignableTypes = PlaceController.class)
@Order(Ordered.HIGHEST_PRECEDENCE)
class PlaceExceptionHandler {
    @ExceptionHandler(InvalidPlaceInputException.class)
    ProblemDetail invalidInput(InvalidPlaceInputException exception, HttpServletRequest request) {
        var problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, exception.getMessage());
        if ("POST".equals(request.getMethod())) {
            problem.setProperty("code", "invalid_request");
        }
        return problem;
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ProblemDetail malformedInput(HttpMessageNotReadableException exception) {
        return problem(HttpStatus.BAD_REQUEST, "invalid_request", "The place request contains invalid or missing fields.");
    }

    @ExceptionHandler({DataAccessResourceFailureException.class, CannotCreateTransactionException.class,
            TransactionSystemException.class, QueryTimeoutException.class})
    ProblemDetail storageUnavailable(Exception exception) {
        return problem(HttpStatus.SERVICE_UNAVAILABLE, "storage_unavailable", "Place storage is unavailable.");
    }

    private static ProblemDetail problem(HttpStatus status, String code, String detail) {
        var problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setProperty("code", code);
        return problem;
    }
}
