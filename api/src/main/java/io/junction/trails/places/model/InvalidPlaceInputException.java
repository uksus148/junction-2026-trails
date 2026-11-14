package io.junction.trails.places.model;

public class InvalidPlaceInputException extends RuntimeException {
    public InvalidPlaceInputException(String message) {
        super(message);
    }
}
