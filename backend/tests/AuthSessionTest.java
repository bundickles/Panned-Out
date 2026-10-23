import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

/** Deterministically verifies expiry without sleeping or weakening production TTLs. */
public class AuthSessionTest {
    private static final class TestClock extends Clock {
        long now = 1_000_000L;
        public ZoneId getZone() { return ZoneOffset.UTC; }
        public Clock withZone(ZoneId zone) { return this; }
        public Instant instant() { return Instant.ofEpochMilli(now); }
        public long millis() { return now; }
    }

    public static void main(String[] args) throws Exception {
        Path directory = Files.createTempDirectory("panned-session-test-");
        TestClock clock = new TestClock();
        AuthService auth = new AuthService(directory, clock);
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/auth/", exchange -> {
            try { auth.handle(exchange); }
            catch (RecipeServer.ApiError error) {
                RecipeServer.respond(exchange, error.status, "{}");
            } finally { exchange.close(); }
        });
        server.start();
        try {
            String url = "http://127.0.0.1:" + server.getAddress().getPort();
            HttpClient client = HttpClient.newHttpClient();
            HttpResponse<String> registered = client.send(HttpRequest.newBuilder(URI.create(url + "/api/auth/register"))
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .POST(HttpRequest.BodyPublishers.ofString("email=expiry%40example.com&password=long+enough+expiry+password"))
                    .build(), HttpResponse.BodyHandlers.ofString());
            if (registered.statusCode() != 201) throw new AssertionError("Registration failed");
            String cookie = registered.headers().firstValue("Set-Cookie").orElseThrow().split(";")[0];
            HttpRequest me = HttpRequest.newBuilder(URI.create(url + "/api/auth/me")).header("Cookie", cookie).build();
            if (client.send(me, HttpResponse.BodyHandlers.ofString()).statusCode() != 200)
                throw new AssertionError("New session rejected");
            clock.now += 8 * 60 * 60 * 1000L;
            if (client.send(me, HttpResponse.BodyHandlers.ofString()).statusCode() != 401)
                throw new AssertionError("Expired session accepted");
            System.out.println("Session expiry test passed.");
        } finally {
            server.stop(0);
            Files.deleteIfExists(directory.resolve("accounts.properties"));
            Files.delete(directory);
        }
    }
}
