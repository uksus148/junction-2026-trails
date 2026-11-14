package io.junction.trails.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "api.cors")
public record ApiCorsProperties(List<String> allowedOrigins) {
    public ApiCorsProperties {
        allowedOrigins = List.copyOf(allowedOrigins);
    }
}
