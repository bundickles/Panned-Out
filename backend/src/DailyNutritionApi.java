import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Planned totals from the caller's current recipes, without guessing missing nutrition. */
final class DailyNutritionApi {
    static void handle(HttpExchange exchange, MealPlanRepository meals, RecipeRepository recipes) throws IOException {
        if (!exchange.getRequestMethod().equals("GET")) {
            exchange.getResponseHeaders().set("Allow", "GET");
            throw new RecipeServer.ApiError(405, "Method not allowed.");
        }
        Map<String, String> query = new LinkedHashMap<>();
        String raw = exchange.getRequestURI().getRawQuery();
        if (raw != null) for (String pair : raw.split("&", -1)) {
            String[] parts = pair.split("=", 2);
            String key = URLDecoder.decode(parts[0], StandardCharsets.UTF_8);
            if (parts.length != 2 || !List.of("start", "end").contains(key) || query.containsKey(key))
                throw new IllegalArgumentException("Supply start and end dates once each.");
            query.put(key, URLDecoder.decode(parts[1], StandardCharsets.UTF_8));
        }
        LocalDate start = LocalDate.parse(MealPlanRepository.date(query.get("start")));
        LocalDate end = LocalDate.parse(MealPlanRepository.date(query.get("end")));
        long difference = ChronoUnit.DAYS.between(start, end);
        if (difference < 0 || difference >= 366)
            throw new IllegalArgumentException("Choose a date range of 1 to 366 days, with start on or before end.");

        Map<String, Day> days = new LinkedHashMap<>();
        for (int offset = 0; offset <= difference; offset++) {
            String date = start.plusDays(offset).toString();
            days.put(date, new Day(date));
        }
        List<String> warnings = new ArrayList<>();
        // Same lock order as recipe/calendar changes; never combine another account's files.
        synchronized (recipes) {
            synchronized (meals) {
                Map<Integer, Recipe> byId = new LinkedHashMap<>();
                for (Recipe recipe : recipes.getRecipes()) byId.put(recipe.getId(), recipe);
                for (MealPlanRepository.Meal meal : meals.getMeals()) {
                    Day day = days.get(meal.date);
                    if (day == null) continue;
                    Recipe recipe = byId.get(meal.recipeId);
                    day.add(recipe);
                    if (recipe == null)
                        warnings.add("{\"message\":\"Recipe unavailable; this day's nutrition is incomplete.\","
                                + "\"mealId\":" + RecipeServer.quote(meal.id) + ",\"recipeId\":" + meal.recipeId
                                + ",\"date\":" + RecipeServer.quote(meal.date) + "}");
                }
            }
        }
        RecipeServer.respond(exchange, 200, "{\"start\":" + RecipeServer.quote(start.toString())
                + ",\"end\":" + RecipeServer.quote(end.toString()) + ",\"days\":"
                + days.values().stream().map(Day::json).collect(Collectors.joining(",", "[", "]"))
                + ",\"warnings\":[" + String.join(",", warnings) + "]}");
    }

    private static final class Day {
        final String date;
        final long[] totals = new long[Recipe.NUTRIENTS.size()];
        final int[] missing = new int[Recipe.NUTRIENTS.size()];
        int mealCount;

        Day(String date) { this.date = date; }

        void add(Recipe recipe) {
            mealCount++;
            for (int i = 0; i < Recipe.NUTRIENTS.size(); i++) {
                String nutrient = Recipe.NUTRIENTS.get(i);
                if (recipe == null || !recipe.hasNutrition(nutrient)) missing[i]++;
                else totals[i] += recipe.nutrition(nutrient);
            }
        }

        String json() {
            StringBuilder result = new StringBuilder("{\"date\":").append(RecipeServer.quote(date))
                    .append(",\"mealCount\":").append(mealCount);
            boolean complete = true;
            List<String> missingFields = new ArrayList<>();
            for (int i = 0; i < Recipe.NUTRIENTS.size(); i++) {
                String field = RecipeServer.quote(Recipe.NUTRIENTS.get(i));
                result.append(',').append(field).append(':')
                        .append(missing[i] == 0 ? Long.toString(totals[i]) : "null");
                missingFields.add(field + ":" + missing[i]);
                if (missing[i] > 0) complete = false;
            }
            return result.append(",\"missingNutrition\":{").append(String.join(",", missingFields))
                    .append("},\"complete\":").append(complete).append('}').toString();
        }
    }
}
