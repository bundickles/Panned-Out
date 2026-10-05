import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

/** Loopback API with session authentication and account-scoped recipe storage. */
public class RecipeServer {
    static final class ApiError extends RuntimeException {
        final int status;
        ApiError(int status, String message) {
            super(message);
            this.status = status;
        }
    }

    public static void main(String[] args) throws Exception {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8080;
        // Keep legacy shared data untouched and use the team's stable default path.
        Path legacy = args.length > 1 ? Path.of(args[1]).toAbsolutePath().normalize()
                : RecipeRepository.defaultStorageFile();
        Path accounts = legacy.resolveSibling(legacy.getFileName() + ".accounts");
        AuthService auth = new AuthService(accounts);
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/api/", exchange -> {
            try {
                // Cross-origin forms cannot set this header; no CORS permission is granted.
                if (!exchange.getRequestMethod().equals("GET")
                        && (!"1".equals(exchange.getRequestHeaders().getFirst("X-Panned-Out-Request"))
                            || "cross-site".equals(exchange.getRequestHeaders().getFirst("Sec-Fetch-Site"))))
                    throw new ApiError(403, "Request verification failed.");
                if (exchange.getRequestURI().getPath().startsWith("/api/auth/")) {
                    auth.handle(exchange);
                } else if (exchange.getRequestURI().getPath().startsWith("/api/recipes")) {
                    handle(exchange, auth.recipes(exchange));
                } else {
                    respond(exchange, 404, "{\"error\":\"Not found\"}");
                }
            } catch (ApiError e) {
                respond(exchange, e.status, "{\"error\":" + quote(e.getMessage()) + "}");
            } catch (IllegalArgumentException e) {
                respond(exchange, 400, "{\"error\":" + quote(e.getMessage()) + "}");
            } catch (UncheckedIOException | IOException e) {
                respond(exchange, 500, "{\"error\":\"Storage unavailable. Please try again.\"}");
            } finally {
                exchange.close();
            }
        });
        server.start();
        System.out.println("Recipe API: http://127.0.0.1:" + server.getAddress().getPort());
        System.out.println("Account storage: " + accounts);
    }
    private static void handle(HttpExchange exchange, RecipeRepository repository) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        boolean updating = path.matches("/api/recipes/[0-9]+") && method.equals("PUT");
        if (path.equals("/api/recipes") || updating) {
            if (method.equals("GET") && !updating) {
                respond(exchange, 200, repository.getRecipes().stream()
                        .map(RecipeServer::json).collect(Collectors.joining(",", "[", "]")));
            } else if (method.equals("POST") || updating) {
                Map<String, String> fields = form(exchange);
                String name = required(fields, "name");
                String ingredients = required(fields, "ingredients");
                String instructions = required(fields, "instructions");
                String category = required(fields, "category");
                if (!java.util.List.of("High Protein", "Low Calorie", "Keto", "My Recipes").contains(category))
                    throw new IllegalArgumentException("Choose a valid category");
                String difficulty = required(fields, "difficulty");
                if (!java.util.List.of("Easy", "Medium", "Hard").contains(difficulty))
                    throw new IllegalArgumentException("Choose a valid difficulty");
                synchronized (repository) {
                    int id = updating ? Integer.parseInt(path.substring(path.lastIndexOf('/') + 1)) : Math.addExact(repository.getRecipes().stream().mapToInt(Recipe::getId).max().orElse(0), 1);
                    Recipe existing = updating ? repository.getRecipes().stream().filter(r -> r.getId() == id).findFirst().orElse(null) : null;
                    if (updating && existing == null) {
                        respond(exchange, 404, "{\"error\":\"Recipe not found\"}");
                        return;
                    }
                    Recipe recipe = new Recipe(id, name, category, difficulty,
                            number(fields, "prepTime"), number(fields, "calories"), number(fields, "protein"),
                            number(fields, "fat"), number(fields, "carbohydrates"), number(fields, "fiber"), updating ? existing.getImage() : "",
                            ingredients, instructions, required(fields, "mealType"));
                    if (updating) repository.updateRecipe(recipe);
                    else repository.addRecipe(recipe);
                    respond(exchange, updating ? 200 : 201, json(recipe));
                }
            } else {
                exchange.getResponseHeaders().set("Allow", "GET, POST");
                respond(exchange, 405, "{\"error\":\"Method not allowed\"}");
            }
        } else if (path.matches("/api/recipes/[0-9]+") && method.equals("DELETE")) {
            boolean deleted = repository.deleteRecipe(Integer.parseInt(path.substring(path.lastIndexOf('/') + 1)));
            respond(exchange, deleted ? 200 : 404, deleted ? "{}" : "{\"error\":\"Recipe not found\"}");
        } else {
            respond(exchange, 404, "{\"error\":\"Not found\"}");
        }
    }

    static Map<String, String> form(HttpExchange exchange) throws IOException {
        String type = exchange.getRequestHeaders().getFirst("Content-Type");
        if (type == null || !type.split(";")[0].trim().equalsIgnoreCase("application/x-www-form-urlencoded"))
            throw new ApiError(415, "Expected form-encoded fields.");
        byte[] body = exchange.getRequestBody().readNBytes(65537);
        if (body.length > 65536) throw new ApiError(413, "Request is too large.");
        Map<String, String> fields = new HashMap<>();
        for (String pair : new String(body, StandardCharsets.UTF_8).split("&")) {
            String[] parts = pair.split("=", 2);
            fields.put(URLDecoder.decode(parts[0], StandardCharsets.UTF_8),
                    parts.length == 2 ? URLDecoder.decode(parts[1], StandardCharsets.UTF_8) : "");
        }
        return fields;
    }
    private static String required(Map<String, String> fields, String key) {
        String value = fields.getOrDefault(key, "").trim();
        if (value.isEmpty() || value.length() > 10000) throw new IllegalArgumentException("Enter a valid " + key);
        return value;
    }

    private static int number(Map<String, String> fields, String key) {
        try {
            int value = Integer.parseInt(fields.getOrDefault(key, "0"));
            if (value < 0 || value > 100000) throw new NumberFormatException();
            return value;
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(key + " must be a whole number between 0 and 100000");
        }
    }

    static String quote(String value) {
        if (value == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (char c : value.toCharArray()) {
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 32) out.append(String.format("\\u%04x", (int) c));
            else out.append(c);
        }
        return out.append('"').toString();
    }

    private static String json(Recipe r) {
        return "{\"id\":" + r.getId() + ",\"name\":" + quote(r.getName())
                + ",\"category\":" + quote(r.getCategory()) + ",\"difficulty\":" + quote(r.getDifficulty())
                + ",\"prepTime\":" + r.getPrepTime() + ",\"calories\":" + r.getCalories()
                + ",\"protein\":" + r.getProtein() + ",\"fat\":" + r.getFat()
                + ",\"carbohydrates\":" + r.getCarbohydrates() + ",\"fiber\":" + r.getFiber()
                + ",\"image\":" + quote(r.getImage()) + ",\"ingredients\":" + quote(r.getIngredients())
                + ",\"instructions\":" + quote(r.getInstructions()) + ",\"mealType\":" + quote(r.getMealType()) + "}";
    }

    static void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
    }
}
