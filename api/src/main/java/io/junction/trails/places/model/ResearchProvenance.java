package io.junction.trails.places.model;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Set;

public record ResearchProvenance(String sourceUrl, String osmType, long osmId) {
    public ResearchProvenance {
        if (osmType == null || !Set.of("node", "way", "relation").contains(osmType) || osmId <= 0) {
            throw new InvalidPlaceInputException("provenance requires a valid osmType and a positive 64-bit osmId");
        }
        try {
            URI url = sourceUrl == null ? null : new URI(sourceUrl);
            if (url == null || !("http".equalsIgnoreCase(url.getScheme()) || "https".equalsIgnoreCase(url.getScheme()))
                    || url.getHost() == null || url.getRawUserInfo() != null
                    || url.getPort() > 65535) {
                throw new InvalidPlaceInputException("provenance.sourceUrl must be an HTTP(S) URL without credentials");
            }
        } catch (URISyntaxException exception) {
            throw new InvalidPlaceInputException("provenance.sourceUrl must be a valid HTTP(S) URL");
        }
    }
}
