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

/** Local demo API. Bind to loopback; authentication is a separate team task. */
public class RecipeServer {
    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8080;
        Path storage = args.length > 1 ? Path.of(args[1]).toAbsolutePath().normalize()
                : RecipeRepository.defaultStorageFile();
        RecipeRepository repository = new RecipeRepository(storage);
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/api/recipes", exchange -> {
            try {
                handle(exchange, repository);
            } catch (IllegalArgumentException e) {
                respond(exchange, 400, "{\"error\":" + quote(e.getMessage()) + "}");
            } catch (UncheckedIOException e) {
                respond(exchange, 500, "{\"error\":\"Recipe storage unavailable. Please try again.\"}");
            } finally {
                exchange.close();
            }
        });
        server.start();
        System.out.println("Recipe API: http://127.0.0.1:" + server.getAddress().getPort());
        System.out.println("Recipe storage: " + storage);
    }

    private static void handle(HttpExchange exchange, RecipeRepository repository) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        if (path.equals("/api/recipes")) {
            if (method.equals("GET")) {
                respond(exchange, 200, repository.getRecipes().stream()
                        .map(RecipeServer::json).collect(Collectors.joining(",", "[", "]")));
            } else if (method.equals("POST")) {
                String type = exchange.getRequestHeaders().getFirst("Content-Type");
                if (type == null || !type.split(";")[0].trim().equalsIgnoreCase("application/x-www-form-urlencoded")) {
                    respond(exchange, 415, "{\"error\":\"Expected form-encoded recipe\"}");
                    return;
                }
                byte[] body = exchange.getRequestBody().readNBytes(65537);
                if (body.length > 65536) {
                    respond(exchange, 413, "{\"error\":\"Recipe is too large\"}");
                    return;
                }
                Map<String, String> fields = new HashMap<>();
                for (String pair : new String(body, StandardCharsets.UTF_8).split("&")) {
                    String[] parts = pair.split("=", 2);
                    fields.put(URLDecoder.decode(parts[0], StandardCharsets.UTF_8),
                            parts.length == 2 ? URLDecoder.decode(parts[1], StandardCharsets.UTF_8) : "");
                }
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
                    int id = Math.addExact(repository.getRecipes().stream().mapToInt(Recipe::getId).max().orElse(0), 1);
                    Recipe recipe = new Recipe(id, name, category, difficulty,
                            number(fields, "prepTime"), number(fields, "calories"), number(fields, "protein"),
                            number(fields, "fat"), number(fields, "carbohydrates"), number(fields, "fiber"), "",
                            ingredients, instructions, required(fields, "mealType"));
                    repository.addRecipe(recipe);
                    respond(exchange, 201, json(recipe));
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

    private static void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
    }
}
