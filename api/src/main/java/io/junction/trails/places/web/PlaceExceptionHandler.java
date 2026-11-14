package io.junction.trails.places.web;

import io.junction.trails.places.model.InvalidPlaceInputException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice(assignableTypes = PlaceController.class)
class PlaceExceptionHandler {
    @ExceptionHandler(InvalidPlaceInputException.class)
    ProblemDetail invalidInput(InvalidPlaceInputException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, exception.getMessage());
    }
}
