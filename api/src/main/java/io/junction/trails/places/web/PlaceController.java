package io.junction.trails.places.web;

import io.junction.trails.places.application.PlaceService;
import io.junction.trails.places.model.BoundingBox;
import io.junction.trails.places.model.InvalidPlaceInputException;
import io.junction.trails.places.model.Place;
import java.util.Arrays;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
class PlaceController {
    private final PlaceService places;

    @GetMapping("/api/places")
    List<Place> search(@RequestParam String bbox, @RequestParam(defaultValue = "") String tags) {
        BoundingBox bounds = BoundingBox.parse(bbox);
        List<String> requestedTags = tags.isBlank() ? List.of()
                : Arrays.stream(tags.split(",", -1)).map(String::strip).distinct().toList();
        if (requestedTags.contains("")) {
            throw new InvalidPlaceInputException("tags must be a comma-separated list of non-empty values");
        }
        return places.search(bounds, requestedTags);
    }

    @PostMapping("/api/places")
    ResponseEntity<Place> create(@RequestBody CreatePlaceRequest request) {
        var result = places.create(request.toCommand(), request.toProvenance());
        return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK).body(result.place());
    }
}
