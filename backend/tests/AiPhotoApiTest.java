import com.sun.net.httpserver.HttpServer;
import java.awt.image.BufferedImage;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.atomic.*;
import java.util.zip.CRC32;
import javax.imageio.ImageIO;

/** Real application/auth HTTP tests plus a local fake Gemini provider. No API key needed. */
public class AiPhotoApiTest {
    static int checks;
    static void check(boolean value, String why) { checks++; if (!value) throw new AssertionError(why); }
    static void error(int status, Runnable action) {
        try { action.run(); throw new AssertionError("Expected error " + status); }
        catch (RecipeServer.ApiError e) { check(status == e.status, "Status: " + e.status); }
    }
    static byte[] image(String format) throws IOException {
        BufferedImage image = new BufferedImage(48, 32, BufferedImage.TYPE_INT_RGB);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        ImageIO.write(image, format, bytes); return bytes.toByteArray();
    }
    static String envelope(String draft) {
        return "{\"candidates\":[{\"finishReason\":\"STOP\",\"content\":{\"parts\":[{\"text\":" + RecipeServer.quote(draft) + "}]}}]}";
    }
    static String draft = "{\"found\":true,\"name\":\"Rice bowl\",\"ingredients\":[\"1 cup rice\",\"1 cup beans\"],\"steps\":[\"Cook rice.\",\"Add cooked beans.\"]}";
    static HttpResponse<String> call(HttpClient client, String url, String method, String type, byte[] bytes, boolean verified) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(5));
        if (type != null) request.header("Content-Type", type);
        if (verified) request.header("X-Panned-Out-Request", "1");
        return client.send(request.method(method, bytes == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofByteArray(bytes)).build(), HttpResponse.BodyHandlers.ofString());
    }
    public static void main(String[] args) throws Exception {
        byte[] png = image("png"), jpeg = image("jpeg");
        check(ImageIO.read(new ByteArrayInputStream(AiPhotoApi.normalize(png, "image/png"))) != null, "Valid PNG normalizes");
        check(AiPhotoApi.normalize(jpeg, "image/jpeg")[0] == (byte) 0xff, "JPEG normalizes");
        error(415, () -> AiPhotoApi.normalize(png, "image/jpeg"));
        error(400, () -> AiPhotoApi.normalize(new byte[0], "image/png"));
        error(400, () -> AiPhotoApi.normalize(new byte[]{1, 2, 3}, "image/png"));
        byte[] huge = png.clone();
        java.nio.ByteBuffer.wrap(huge, 16, 8).putInt(100000).putInt(100000);
        CRC32 crc = new CRC32(); crc.update(huge, 12, 17);
        java.nio.ByteBuffer.wrap(huge, 29, 4).putInt((int) crc.getValue());
        error(413, () -> AiPhotoApi.normalize(huge, "image/png"));
        BufferedImage wide = new BufferedImage(2048, 16, BufferedImage.TYPE_INT_RGB);
        ByteArrayOutputStream wideBytes = new ByteArrayOutputStream();
        ImageIO.write(wide, "png", wideBytes);
        BufferedImage resized = ImageIO.read(new ByteArrayInputStream(AiPhotoApi.normalize(wideBytes.toByteArray(), "image/png")));
        check(resized.getWidth() <= 1024 && resized.getHeight() <= 1024, "Large images downsampled");
        String parsed = GeminiPhotoClient.parseResponse(envelope(draft));
        check(parsed.contains("requiresConfirmation\":true"), "Review required");
        check(parsed.contains("Rice bowl"), "Draft returned");
        check(GeminiPhotoClient.parseResponse(envelope("{\"found\":false,\"name\":\"\",\"ingredients\":[],\"steps\":[]}")).contains("no_result"), "No food");
        error(502, () -> GeminiPhotoClient.parseResponse("invalid json"));
        error(502, () -> GeminiPhotoClient.parseResponse(envelope(draft.replace("Rice bowl", "x".repeat(121)))));
        error(502, () -> GeminiPhotoClient.parseResponse(envelope("{\"found\":true,\"name\":\"Rice\",\"ingredients\":[],\"steps\":[]}")));
        error(422, () -> GeminiPhotoClient.parseResponse("{\"promptFeedback\":{\"blockReason\":\"SAFETY\"}}"));
        error(502, () -> GeminiPhotoClient.parseResponse("{\"candidates\":[{\"finishReason\":\"MAX_TOKENS\"}]}"));
        for (String malformed : List.of("[1,]", "{\"a\":1,\"a\":2}", "01", "\"\\u+123\"", "[".repeat(35))) {
            try { PhotoJson.parse(malformed); throw new AssertionError("Malformed JSON accepted"); }
            catch (IllegalArgumentException expected) { checks++; }
        }
        AtomicInteger status = new AtomicInteger(200), calls = new AtomicInteger();
        AtomicReference<String> reply = new AtomicReference<>(envelope(draft));
        AtomicReference<String> upstreamBody = new AtomicReference<>(), upstreamKey = new AtomicReference<>();
        AtomicInteger delay = new AtomicInteger();
        HttpServer fake = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        fake.createContext("/generate", exchange -> {
            calls.incrementAndGet();
            upstreamBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            upstreamKey.set(exchange.getRequestHeaders().getFirst("x-goog-api-key"));
            try { Thread.sleep(delay.get()); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            try { RecipeServer.respond(exchange, status.get(), reply.get()); } finally { exchange.close(); }
        });
        fake.start();
        URI endpoint = URI.create("http://127.0.0.1:" + fake.getAddress().getPort() + "/generate");
        Path dir = Files.createTempDirectory("photo-api-test-");
        HttpServer app = RecipeServer.createServer(0, dir.resolve("recipes.properties"), new AiPhotoApi(new GeminiPhotoClient("fake-secret", endpoint, Duration.ofSeconds(2))));
        app.start();
        try {
            String base = "http://127.0.0.1:" + app.getAddress().getPort();
            String url = base + "/api/ai/photo-recipe";
            CookieManager cookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
            HttpClient client = HttpClient.newBuilder().cookieHandler(cookies).build();
            check(call(client, url, "POST", "image/png", png, true).statusCode() == 401, "Signed out POST rejected");
            check(call(client, url, "GET", null, null, false).statusCode() == 401, "Signed out GET rejected");
            byte[] registration = "email=photo%40example.com&password=a+long+photo+test+password".getBytes(StandardCharsets.UTF_8);
            check(call(client, base + "/api/auth/register", "POST", "application/x-www-form-urlencoded", registration, true).statusCode() == 201, "Register");
            cookies.getCookieStore().getCookies().forEach(cookie -> cookie.setVersion(0));
            check(call(client, url, "GET", null, null, false).body().contains("available\":true"), "Configured status");
            check(call(client, url, "POST", "image/png", png, false).statusCode() == 403, "CSRF header required");
            check(call(client, url, "DELETE", null, null, true).statusCode() == 405, "Methods enforced");
            check(call(client, url, "POST", "image/gif", png, true).statusCode() == 415, "Wrong type");
            check(call(client, url, "POST", "image/jpeg", png, true).statusCode() == 415, "Spoofed type");
            check(call(client, url, "POST", "image/png", new byte[]{1}, true).statusCode() == 400, "Invalid bytes");
            check(call(client, url, "POST", "image/png", new byte[0], true).statusCode() == 400, "Empty upload");
            check(call(client, url, "POST", "image/png", huge, true).statusCode() == 413, "Pixel limit");
            check(call(client, url, "POST", "image/png", new byte[AiPhotoApi.MAX_BYTES + 1], true).statusCode() == 413, "Byte limit");
            check(calls.get() == 0, "Invalid requests never reach provider");
            HttpResponse<String> response = call(client, url, "POST", "image/png", png, true);
            check(response.statusCode() == 200 && response.body().contains("Rice bowl"), "Photo returns draft");
            check(upstreamKey.get().equals("fake-secret") && !upstreamBody.get().contains("fake-secret"), "Key only in header");
            Map<?, ?> request = (Map<?, ?>) PhotoJson.parse(upstreamBody.get());
            Map<?, ?> content = (Map<?, ?>) ((List<?>) request.get("contents")).get(0);
            Map<?, ?> part = (Map<?, ?>) ((List<?>) content.get("parts")).get(0);
            Map<?, ?> inline = (Map<?, ?>) part.get("inlineData");
            check(inline.get("mimeType").equals("image/jpeg"), "Normalized MIME");
            check(ImageIO.read(new ByteArrayInputStream(Base64.getDecoder().decode((String) inline.get("data")))) != null, "Provider receives image");
            check(!upstreamBody.get().contains("photo@example.com"), "Account data not sent");
            reply.set(envelope("{\"found\":false,\"name\":\"\",\"ingredients\":[],\"steps\":[]}"));
            check(call(client, url, "POST", "image/jpeg", jpeg, true).body().contains("no_result"), "No-result endpoint");
            reply.set("invalid-json");
            check(call(client, url, "POST", "image/png", png, true).statusCode() == 502, "Malformed provider reply");
            status.set(429); reply.set("private-provider-details");
            response = call(client, url, "POST", "image/png", png, true);
            check(response.statusCode() == 429 && !response.body().contains("private-provider-details"), "Quota and sanitized error");
            status.set(500);
            check(call(client, url, "POST", "image/png", png, true).statusCode() == 502, "Provider outage");
            status.set(403);
            check(call(client, url, "POST", "image/png", png, true).statusCode() == 503, "Configuration failure");
            check(call(client, url, "POST", "image/png", png, true).statusCode() == 429 && calls.get() == 6, "Local rate limit");
            check(call(client, base + "/api/recipes", "GET", null, null, false).body().equals("[]"), "Nothing saved, server remains healthy");
            status.set(200); reply.set(envelope(draft)); delay.set(300);
            error(504, () -> new GeminiPhotoClient("fake-secret", endpoint, Duration.ofMillis(50)).generate(jpeg));
        } finally {
            app.stop(0); ((ExecutorService) app.getExecutor()).shutdownNow(); fake.stop(0);
            try (java.util.stream.Stream<Path> paths = Files.walk(dir)) {
                for (Path path : (Iterable<Path>) paths.sorted(Comparator.reverseOrder())::iterator) Files.delete(path);
            }
        }
        missingKey();
        System.out.println("AiPhotoApiTest: " + checks + " checks passed");
    }
    static void missingKey() throws Exception {
        Path dir = Files.createTempDirectory("photo-missing-key-");
        HttpServer app = RecipeServer.createServer(0, dir.resolve("recipes.properties"),
            new AiPhotoApi(new GeminiPhotoClient("", URI.create("http://127.0.0.1:1/not-used"), Duration.ofSeconds(1))));
        app.start();
        try {
            String base = "http://127.0.0.1:" + app.getAddress().getPort();
            CookieManager cookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
            HttpClient client = HttpClient.newBuilder().cookieHandler(cookies).build();
            byte[] form = "email=empty%40example.com&password=a+long+photo+test+password".getBytes(StandardCharsets.UTF_8);
            check(call(client, base + "/api/auth/register", "POST", "application/x-www-form-urlencoded", form, true).statusCode() == 201, "No-key app still registers");
            cookies.getCookieStore().getCookies().forEach(cookie -> cookie.setVersion(0));
            check(call(client, base + "/api/ai/photo-recipe", "GET", null, null, false).body().contains("available\":false"), "Missing-key availability");
            check(call(client, base + "/api/ai/photo-recipe", "POST", "image/png", image("png"), true).statusCode() == 503, "Missing key handled without provider call");
        } finally {
            app.stop(0); ((ExecutorService) app.getExecutor()).shutdownNow();
            try (java.util.stream.Stream<Path> paths = Files.walk(dir)) {
                for (Path path : (Iterable<Path>) paths.sorted(Comparator.reverseOrder())::iterator) Files.delete(path);
            }
        }
    }

}
