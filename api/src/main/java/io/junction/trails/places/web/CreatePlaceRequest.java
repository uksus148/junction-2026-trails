package io.junction.trails.places.web;

import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.databind.JsonNode;
import io.junction.trails.places.model.InvalidPlaceInputException;
import io.junction.trails.places.model.NewPlace;
import io.junction.trails.places.model.ResearchProvenance;
import java.util.List;

record CreatePlaceRequest(String name, Double lat, Double lon, List<String> tags, JsonNode provenance) {
    NewPlace toCommand() {
        if (lat == null || lon == null) {
            throw new InvalidPlaceInputException("lat and lon are required");
        }
        return new NewPlace(name, lat, lon, tags);
    }

    ResearchProvenance toProvenance() {
        if (provenance == null) {
            return null;
        }
        if (!provenance.isObject() || provenance.size() != 3
                || !provenance.has("sourceUrl") || !provenance.get("sourceUrl").isTextual()
                || !provenance.has("osmType") || !provenance.get("osmType").isTextual()
                || !provenance.has("osmId") || !provenance.get("osmId").isIntegralNumber()
                || !provenance.get("osmId").canConvertToLong()) {
            throw new InvalidPlaceInputException("provenance requires sourceUrl, osmType, and an integer osmId");
        }
        return new ResearchProvenance(provenance.get("sourceUrl").textValue(),
                provenance.get("osmType").textValue(), provenance.get("osmId").longValue());
    }

    @JsonAnySetter
    void unknownField(String field, JsonNode value) {
        throw new InvalidPlaceInputException("Unknown place request field");
    }
}
