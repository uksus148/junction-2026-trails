package io.junction.trails.places.web;

import io.junction.trails.places.model.BoundingBox;
import io.junction.trails.places.model.Place;
import io.junction.trails.places.persistence.PlaceRepository;
import java.util.Arrays;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
class PlaceController {
    private final PlaceRepository places;

    @GetMapping("/api/places")
    List<Place> search(@RequestParam String bbox, @RequestParam(defaultValue = "") String tags) {
        BoundingBox bounds = BoundingBox.parse(bbox);
        List<String> requestedTags = tags.isBlank() ? List.of()
                : Arrays.stream(tags.split(",", -1)).map(String::strip).distinct().toList();
        if (requestedTags.contains("")) {
            throw new IllegalArgumentException("tags must be a comma-separated list of non-empty values");
        }
        return places.search(bounds, requestedTags);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ProblemDetail invalidParameter(IllegalArgumentException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, exception.getMessage());
    }
}
