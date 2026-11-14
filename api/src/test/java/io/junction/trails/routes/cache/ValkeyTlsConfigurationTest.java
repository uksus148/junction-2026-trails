package io.junction.trails.routes.cache;

import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;

import static org.assertj.core.api.Assertions.assertThat;

class ValkeyTlsConfigurationTest {
    @Test
    void bindsAnAivenStyleEndpointWithTlsVerificationAndBoundedTimeoutsWithoutConnecting() {
        new ApplicationContextRunner().withConfiguration(AutoConfigurations.of(RedisAutoConfiguration.class))
                .withPropertyValues("spring.data.redis.url=rediss://fixture-user:fixture-password@aiven.example:1234/0",
                        "spring.data.redis.connect-timeout=2s", "spring.data.redis.timeout=3s")
                .run(context -> {
                    var connection = context.getBean(LettuceConnectionFactory.class);
                    var client = connection.getClientConfiguration();
                    assertThat(connection.getHostName()).isEqualTo("aiven.example");
                    assertThat(connection.getPort()).isEqualTo(1234);
                    assertThat(client.isUseSsl()).isTrue();
                    assertThat(client.isVerifyPeer()).isTrue();
                    assertThat(client.getCommandTimeout()).isEqualTo(Duration.ofSeconds(3));
                    assertThat(client.getClientOptions().orElseThrow().getSocketOptions().getConnectTimeout())
                            .isEqualTo(Duration.ofSeconds(2));
                });
    }
}
