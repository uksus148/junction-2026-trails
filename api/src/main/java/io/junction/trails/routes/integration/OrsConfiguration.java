package io.junction.trails.routes.integration;

import io.junction.trails.routes.application.RoutingGateway;
import java.net.http.HttpClient;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties(OrsProperties.class)
@RequiredArgsConstructor
public class OrsConfiguration {
    private final OrsProperties properties;
    private final RestClient.Builder builder;

    @Bean
    RoutingGateway routingGateway() {
        var http = HttpClient.newBuilder().connectTimeout(properties.connectTimeout())
                .followRedirects(HttpClient.Redirect.NEVER).build();
        var requests = new JdkClientHttpRequestFactory(http);
        requests.setReadTimeout(properties.readTimeout());
        var client = builder.clone().requestFactory(requests)
                .defaultHeader(HttpHeaders.AUTHORIZATION, properties.apiKey()).build();
        return new OrsRoutingGateway(client, properties);
    }
}
