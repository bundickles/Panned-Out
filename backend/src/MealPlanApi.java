import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.util.Map;
import java.util.stream.Collectors;

/** Calendar endpoints use the same session and request verification as recipes. */
final class MealPlanApi {
    static void handle(HttpExchange exchange, MealPlanRepository meals, RecipeRepository recipes) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        if (path.equals("/api/meals")) {
            if (method.equals("GET")) {
                RecipeServer.respond(exchange, 200, meals.getMeals().stream()
                        .map(MealPlanApi::json).collect(Collectors.joining(",", "[", "]")));
            } else if (method.equals("POST")) {
                Map<String, String> fields = RecipeServer.form(exchange);
                int recipeId;
                try { recipeId = Integer.parseInt(fields.getOrDefault("recipeId", "")); }
                catch (NumberFormatException e) { throw new IllegalArgumentException("Choose a recipe."); }
                Recipe recipe = recipes.getRecipes().stream().filter(r -> r.getId() == recipeId).findFirst()
                        .orElseThrow(() -> new RecipeServer.ApiError(404, "Recipe not found. Choose one of your saved recipes."));
                MealPlanRepository.Meal saved = meals.add(fields.get("date"), fields.getOrDefault("mealType", ""), recipe);
                RecipeServer.respond(exchange, 201, json(saved));
            } else {
                exchange.getResponseHeaders().set("Allow", "GET, POST");
                throw new RecipeServer.ApiError(405, "Method not allowed.");
            }
        } else if (path.matches("/api/meals/[0-9a-f-]{36}") && method.equals("DELETE")) {
            if (!meals.remove(path.substring(path.lastIndexOf('/') + 1)))
                throw new RecipeServer.ApiError(404, "Meal not found.");
            RecipeServer.respond(exchange, 200, "{}");
        } else {
            throw new RecipeServer.ApiError(404, "Not found.");
        }
    }

    private static String json(MealPlanRepository.Meal meal) {
        return "{\"id\":" + RecipeServer.quote(meal.id) + ",\"date\":" + RecipeServer.quote(meal.date)
                + ",\"type\":" + RecipeServer.quote(meal.type) + ",\"recipeId\":" + meal.recipeId
                + ",\"name\":" + RecipeServer.quote(meal.name) + ",\"difficulty\":" + RecipeServer.quote(meal.difficulty)
                + ",\"prepTime\":" + meal.prepTime + "}";
    }
}
