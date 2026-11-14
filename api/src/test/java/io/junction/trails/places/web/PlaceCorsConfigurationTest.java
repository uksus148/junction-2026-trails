package io.junction.trails.places.web;

import io.junction.trails.config.ApiWebConfiguration;
import io.junction.trails.places.persistence.PlaceRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = PlaceController.class, properties = {
        "spring.config.import=",
        "API_CORS_ALLOWED_ORIGINS=http://localhost:5174,https://trails.example.org"
})
@Import(ApiWebConfiguration.class)
class PlaceCorsConfigurationTest {
    @MockitoBean
    PlaceRepository places;

    @Autowired
    MockMvc browser;

    @ParameterizedTest
    @ValueSource(strings = {"http://localhost:5174", "https://trails.example.org"})
    void usesConfiguredFrontendOrigins(String origin) throws Exception {
        browser.perform(get("/api/places").param("bbox", "20,49,21,50")
                        .header(HttpHeaders.ORIGIN, origin))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, origin));
    }

    @Test
    void replacesDefaultOriginWhenConfigured() throws Exception {
        browser.perform(get("/api/places").param("bbox", "20,49,21,50")
                        .header(HttpHeaders.ORIGIN, "http://localhost:5173"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
    }
}
