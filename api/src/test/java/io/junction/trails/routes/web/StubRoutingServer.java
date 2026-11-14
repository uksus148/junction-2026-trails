package io.junction.trails.routes.web;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import lombok.Getter;
import org.springframework.core.io.ClassPathResource;

final class StubRoutingServer implements AutoCloseable {
    private final HttpServer server;
    private final ExecutorService executor = Executors.newCachedThreadPool();
    @Getter
    private final List<Request> requests = new CopyOnWriteArrayList<>();
    private volatile Reply reply;

    StubRoutingServer() throws IOException {
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.setExecutor(executor);
        server.createContext("/ors/v2/directions/foot-hiking/geojson", exchange -> {
            var mapper = new ObjectMapper();
            requests.add(new Request(exchange.getRequestMethod(), exchange.getRequestURI().getPath(),
                    exchange.getRequestHeaders().getFirst("Authorization"), mapper.readTree(exchange.getRequestBody())));
            Reply current = reply;
            try {
                byte[] body = current.body().getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                if (current.headersFirst()) {
                    exchange.sendResponseHeaders(current.status(), body.length);
                    exchange.getResponseBody().flush();
                }
                TimeUnit.MILLISECONDS.sleep(current.delayMillis());
                if (!current.headersFirst()) {
                    exchange.sendResponseHeaders(current.status(), body.length);
                }
                exchange.getResponseBody().write(body);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
            } finally {
                exchange.close();
            }
        });
        reset();
        server.start();
    }

    String baseUrl() {
        return "http://localhost:" + server.getAddress().getPort() + "/ors";
    }

    void reset() throws IOException {
        requests.clear();
        reply = new Reply(200, new ClassPathResource("ors/route.geojson").getContentAsString(StandardCharsets.UTF_8), 0, false);
    }

    void respond(int status, String body, long delayMillis) {
        reply = new Reply(status, body, delayMillis, false);
    }

    void delayBody(long delayMillis) {
        reply = new Reply(200, "{}", delayMillis, true);
    }

    @Override
    public void close() {
        server.stop(0);
        executor.shutdownNow();
    }

    record Request(String method, String path, String authorization, JsonNode body) {
    }

    private record Reply(int status, String body, long delayMillis, boolean headersFirst) {
    }
}
