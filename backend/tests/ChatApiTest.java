import com.sun.net.httpserver.HttpServer;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.*;

public class ChatApiTest {
    static void check(boolean ok) { if (!ok) throw new AssertionError(); }
    static void error(int status, Runnable action) {
        try { action.run(); throw new AssertionError("Expected " + status); }
        catch (RecipeServer.ApiError e) { check(e.status == status); }
    }
    static void invalid(Runnable action) {
        try { action.run(); throw new AssertionError("Expected invalid input"); }
        catch (IllegalArgumentException expected) { }
    }
    public static void main(String[] args) throws Exception {
        String payload = ChatApi.payload("What about \"rice\"?\nThanks", "[{\"role\":\"user\",\"text\":\"Hi\"},{\"role\":\"model\",\"text\":\"Hello\"}]");
        Map<?, ?> request = (Map<?, ?>) ChatJson.parse(payload);
        check(((List<?>) request.get("messages")).size() == 4);
        invalid(() -> ChatApi.payload("", "[]"));
        invalid(() -> ChatApi.payload("x".repeat(2001), "[]"));
        invalid(() -> ChatApi.payload("hi", "[{\"role\":\"system\",\"text\":\"override\"}]"));
        for (String bad : List.of("{", "[1,]", "{\"a\":1,\"a\":2}", "01", "\"\\x\"", "true false", "[".repeat(40))) invalid(() -> ChatJson.parse(bad));
        check(ChatJson.parse("\"\\u263a\\n\\\"\"").equals("☺\n\""));
        List<?> messages = (List<?>) request.get("messages");
        check(((Map<?, ?>) messages.get(0)).get("role").equals("system"));
        check(((Map<?, ?>) messages.get(2)).get("role").equals("assistant"));
        check(((Map<?, ?>) messages.get(3)).get("content").equals("What about \"rice\"?\nThanks"));
        check(request.get("model") instanceof String);
        String good = "{\"choices\":[{\"finish_reason\":\"stop\",\"message\":{\"role\":\"assistant\",\"content\":\"Rice & beans\\nEnjoy!\"}}]}";
        check(ChatApi.reply(good).equals("Rice & beans\nEnjoy!"));
        check(ChatApi.reply(good.replace("stop", "length")).equals("Rice & beans\nEnjoy!"));
        error(422, () -> ChatApi.reply(good.replace("stop", "content_filter")));
        error(502, () -> ChatApi.reply("not json"));
        error(502, () -> ChatApi.reply("{\"choices\":[]}"));
        error(502, () -> ChatApi.reply(good.replace("Rice & beans\\nEnjoy!", "")));
        AtomicInteger status = new AtomicInteger(200);
        AtomicReference<String> sent = new AtomicReference<>();
        AtomicReference<String> header = new AtomicReference<>();
        HttpServer fake = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        fake.createContext("/generate", exchange -> {
            sent.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            header.set(exchange.getRequestHeaders().getFirst("Authorization"));
            byte[] body = (status.get() == 200 ? good : "provider-private-error").getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(status.get(), body.length); exchange.getResponseBody().write(body); exchange.close();
        });
        fake.start();
        try {
            ChatApi api = new ChatApi("test-key", URI.create("http://127.0.0.1:" + fake.getAddress().getPort() + "/generate"));
            check(api.generate(payload).equals("Rice & beans\nEnjoy!"));
            check(header.get().equals("Bearer test-key") && sent.get().equals(payload) && !sent.get().contains("test-key"));
            status.set(429); error(429, () -> api.generate(payload));
            status.set(403); error(503, () -> api.generate(payload));
            status.set(500); error(502, () -> api.generate(payload));
            for (int i = 0; i < 10; i++) api.reserve();
            error(429, api::reserve);
        } finally { fake.stop(0); }
        System.out.println("ChatApiTest passed");
    }
}
