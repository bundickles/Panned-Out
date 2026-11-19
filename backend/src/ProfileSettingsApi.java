import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;

/** Authenticated profile/settings endpoints. UI integration is tracked in SCRUM-90/86. */
final class ProfileSettingsApi {
    static void handle(HttpExchange exchange, ProfileSettingsRepository repository) throws IOException {
        if (exchange.getRequestURI().getRawQuery() != null)
            throw new IllegalArgumentException("This endpoint does not accept query parameters.");
        boolean profile = exchange.getRequestURI().getPath().equals("/api/profile");
        String method = exchange.getRequestMethod();
        String response;
        if (method.equals("GET")) {
            response = profile ? repository.getProfile().json() : repository.getSettings().json();
        } else if (method.equals("PATCH")) {
            response = profile ? repository.updateProfile(RecipeServer.form(exchange)).json()
                    : repository.updateSettings(RecipeServer.form(exchange)).json();
        } else {
            exchange.getResponseHeaders().set("Allow", "GET, PATCH");
            throw new RecipeServer.ApiError(405, "Method not allowed.");
        }
        RecipeServer.respond(exchange, 200, response);
    }
}
