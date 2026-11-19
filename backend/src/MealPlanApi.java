import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.util.Map;
import java.util.stream.Collectors;

/** Calendar endpoints use the same session and request verification as recipes. */
final class MealPlanApi {
    static void handle(HttpExchange exchange, MealPlanRepository meals, RecipeRepository recipes) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        if (path.equals("/api/meals/plan")) {
            if (!method.equals("POST")) {
                exchange.getResponseHeaders().set("Allow", "POST");
                throw new RecipeServer.ApiError(405, "Method not allowed.");
            }
            Map<String, String> fields = RecipeServer.form(exchange);
            String plan = fields.getOrDefault("plan", "");
            if (!java.util.List.of("High Protein", "Low Calorie", "Keto", "Balanced").contains(plan))
                throw new IllegalArgumentException("Choose a premade meal plan.");
            String[] requested = fields.getOrDefault("recipeIds", "").split(",", -1);
            if (requested.length > 31) throw new IllegalArgumentException("Choose at most 31 saved recipes.");
            java.util.List<Recipe> selected = new java.util.ArrayList<>();
            java.util.Set<Integer> seen = new java.util.HashSet<>();
            // Lock in the same order as ordinary recipe operations. Resolve the
            // complete selection before any calendar write, using this account only.
            synchronized (recipes) {
                java.util.List<Recipe> saved = recipes.getRecipes();
                for (String value : requested) {
                    int id;
                    try { id = Integer.parseInt(value); }
                    catch (NumberFormatException e) { throw new IllegalArgumentException("Choose saved recipes for the plan."); }
                    if (!seen.add(id)) throw new IllegalArgumentException("Choose each recipe only once.");
                    Recipe recipe = saved.stream().filter(r -> r.getId() == id).findFirst()
                        .orElseThrow(() -> new RecipeServer.ApiError(404, "A selected recipe is unavailable. Refresh the plan."));
                    if (!plan.equals("Balanced") && !plan.equals(recipe.getCategory()))
                        throw new IllegalArgumentException("A selected recipe does not belong to this plan category.");
                    selected.add(recipe);
                }
                java.util.List<MealPlanRepository.Meal> added = meals.addPlan(fields.get("startDate"),
                    fields.getOrDefault("mealType", "Dinner"), selected);
                RecipeServer.respond(exchange, 201, added.stream().map(MealPlanApi::json)
                    .collect(Collectors.joining(",", "[", "]")));
            }
        } else if (path.equals("/api/meals")) {
            if (method.equals("GET")) {
                RecipeServer.respond(exchange, 200, RecipeCalendarService.currentMeals(recipes, meals).stream()
                        .map(MealPlanApi::json).collect(Collectors.joining(",", "[", "]")));
            } else if (method.equals("POST")) {
                Map<String, String> fields = RecipeServer.form(exchange);
                int recipeId;
                try { recipeId = Integer.parseInt(fields.getOrDefault("recipeId", "")); }
                catch (NumberFormatException e) { throw new IllegalArgumentException("Choose a recipe."); }
                synchronized (recipes) {
                    Recipe recipe = recipes.getRecipes().stream().filter(r -> r.getId() == recipeId).findFirst()
                            .orElseThrow(() -> new RecipeServer.ApiError(404, "Recipe not found. Choose one of your saved recipes."));
                    MealPlanRepository.Meal saved = meals.add(fields.get("date"), fields.getOrDefault("mealType", ""), recipe);
                    RecipeServer.respond(exchange, 201, json(saved));
                }
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
