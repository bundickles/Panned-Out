import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

/** Generates ingredients from the caller's current recipes and scheduled meals. */
final class GeneratedShoppingListApi {
    static void handle(HttpExchange exchange, MealPlanRepository meals, RecipeRepository recipes) throws IOException {
        if (!exchange.getRequestMethod().equals("GET")) {
            exchange.getResponseHeaders().set("Allow", "GET");
            throw new RecipeServer.ApiError(405, "Method not allowed.");
        }
        Map<String, String> query = new LinkedHashMap<>();
        String raw = exchange.getRequestURI().getRawQuery();
        if (raw != null) for (String pair : raw.split("&")) {
            String[] parts = pair.split("=", 2);
            String key = URLDecoder.decode(parts[0], StandardCharsets.UTF_8);
            if (parts.length != 2 || query.containsKey(key)) throw new IllegalArgumentException("Invalid date range query.");
            query.put(key, URLDecoder.decode(parts[1], StandardCharsets.UTF_8));
        }
        String start = MealPlanRepository.date(query.get("start"));
        String end = MealPlanRepository.date(query.get("end"));
        if (start.compareTo(end) > 0) throw new IllegalArgumentException("Start date must be on or before end date.");
        Map<Integer, Recipe> byId = new LinkedHashMap<>();
        for (Recipe recipe : recipes.getRecipes()) byId.put(recipe.getId(), recipe);
        Map<String, Item> items = new LinkedHashMap<>();
        List<String> warnings = new ArrayList<>();
        for (MealPlanRepository.Meal meal : meals.getMeals()) {
            if (meal.date.compareTo(start) < 0 || meal.date.compareTo(end) > 0) continue;
            String source = "{\"mealId\":" + RecipeServer.quote(meal.id) + ",\"recipeId\":" + meal.recipeId
                    + ",\"date\":" + RecipeServer.quote(meal.date) + ",\"recipeName\":" + RecipeServer.quote(meal.name) + "}";
            Recipe recipe = byId.get(meal.recipeId);
            if (recipe == null) {
                warnings.add("{\"message\":\"Recipe unavailable; its ingredients were omitted.\",\"source\":" + source + "}");
                continue;
            }
            // Preserve quantities in each line; only case and whitespace are normalized for grouping.
            String ingredients = recipe.getIngredients();
            if (ingredients == null || ingredients.isBlank()) {
                warnings.add("{\"message\":\"Recipe has no ingredients; its ingredients were omitted.\",\"source\":" + source + "}");
                continue;
            }
            for (String line : ingredients.split("\\R")) {
                String name = line.replaceAll("(?U)\\s+", " ").strip();
                if (name.isEmpty()) continue;
                Item item = items.computeIfAbsent(name.toLowerCase(Locale.ROOT), ignored -> new Item(name));
                item.sources.add(source);
            }
        }
        RecipeServer.respond(exchange, 200, "{\"start\":" + RecipeServer.quote(start) + ",\"end\":" + RecipeServer.quote(end)
                + ",\"items\":" + items.values().stream().map(Item::json).collect(Collectors.joining(",", "[", "]"))
                + ",\"warnings\":" + ("[" + String.join(",", warnings) + "]") + "}");
    }

    private static final class Item {
        final String name;
        final List<String> sources = new ArrayList<>();
        Item(String name) { this.name = name; }
        String json() {
            return "{\"name\":" + RecipeServer.quote(name) + ",\"occurrences\":" + sources.size()
                    + ",\"sources\":[" + String.join(",", sources) + "]}";
        }
    }
}
