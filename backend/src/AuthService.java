import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Clock;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

/** Opaque server-side sessions; a restart signs everybody out, not deletes accounts. */
final class AuthService {
    private static final String COOKIE = "panned_session";
    private static final long SESSION_MS = 8 * 60 * 60 * 1000L;
    private static final long ATTEMPT_WINDOW_MS = 15 * 60 * 1000L;
    private final SecureRandom random = new SecureRandom();
    private final Map<String, Session> sessions = new HashMap<>();
    private final Map<String, AttemptWindow> attempts = new HashMap<>();
    private final Map<String, RecipeRepository> repositories = new HashMap<>();
    private final Map<String, MealPlanRepository> mealPlans = new HashMap<>();
    private final AccountRepository accounts;
    private final Path recipeDirectory;
    private final Clock clock;

    private static final class Session {
        final AccountRepository.Account account;
        final long expires;
        Session(AccountRepository.Account account, long expires) {
            this.account = account;
            this.expires = expires;
        }
    }

    private static final class AttemptWindow {
        int count;
        final long expires;
        AttemptWindow(long expires) { this.expires = expires; }
    }

    AuthService(Path dataDirectory) {
        this(dataDirectory, Clock.systemUTC());
    }

    AuthService(Path dataDirectory, Clock clock) {
        accounts = new AccountRepository(dataDirectory.resolve("accounts.properties"));
        recipeDirectory = dataDirectory.resolve("users");
        this.clock = clock;
    }

    synchronized RecipeRepository recipes(HttpExchange exchange) {
        AccountRepository.Account account = requireSession(exchange).account;
        // The directory comes only from a server-generated account UUID, never request fields.
        return repositories.computeIfAbsent(account.id,
                id -> new RecipeRepository(recipeDirectory.resolve(id).resolve("recipes.properties")));
    }

    synchronized MealPlanRepository meals(HttpExchange exchange) {
        AccountRepository.Account account = requireSession(exchange).account;
        return mealPlans.computeIfAbsent(account.id,
                id -> new MealPlanRepository(recipeDirectory.resolve(id).resolve("meals.properties")));
    }

    synchronized void handle(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        if (path.equals("/api/auth/me") && method.equals("GET")) {
            RecipeServer.respond(exchange, 200, json(requireSession(exchange).account));
        } else if (path.equals("/api/auth/logout") && method.equals("POST")) {
            sessions.remove(token(exchange));
            cookie(exchange, "", 0);
            RecipeServer.respond(exchange, 200, "{}");
        } else if ((path.equals("/api/auth/login") || path.equals("/api/auth/register")) && method.equals("POST")) {
            throttle(exchange);
            Map<String, String> fields = RecipeServer.form(exchange);
            String email = fields.getOrDefault("email", "");
            String password = fields.getOrDefault("password", "");
            boolean registering = path.endsWith("/register");
            AccountRepository.Account account = registering
                    ? accounts.register(email, password) : accounts.authenticate(email, password);
            sessions.remove(token(exchange));
            long now = clock.millis();
            sessions.values().removeIf(session -> session.expires <= now);
            byte[] bytes = new byte[32];
            random.nextBytes(bytes);
            String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
            sessions.put(token, new Session(account, now + SESSION_MS));
            cookie(exchange, token, SESSION_MS / 1000);
            RecipeServer.respond(exchange, registering ? 201 : 200, json(account));
        } else {
            RecipeServer.respond(exchange, 404, "{\"error\":\"Not found\"}");
        }
    }

    private Session requireSession(HttpExchange exchange) {
        String token = token(exchange);
        Session session = sessions.get(token);
        if (session == null || session.expires <= clock.millis()) {
            sessions.remove(token);
            cookie(exchange, "", 0);
            throw new RecipeServer.ApiError(401, "Please sign in to continue.");
        }
        return session;
    }

    private void throttle(HttpExchange exchange) {
        long now = clock.millis();
        attempts.values().removeIf(window -> window.expires <= now);
        String address = exchange.getRemoteAddress().getAddress().getHostAddress();
        AttemptWindow window = attempts.computeIfAbsent(address, ignored -> new AttemptWindow(now + ATTEMPT_WINDOW_MS));
        if (++window.count > 20) {
            exchange.getResponseHeaders().set("Retry-After", Long.toString((window.expires - now + 999) / 1000));
            throw new RecipeServer.ApiError(429, "Too many sign-in attempts. Please try again later.");
        }
    }

    private static String token(HttpExchange exchange) {
        String header = exchange.getRequestHeaders().getFirst("Cookie");
        if (header != null) {
            for (String part : header.split(";")) {
                String[] pair = part.trim().split("=", 2);
                if (pair.length == 2 && pair[0].equals(COOKIE)) return pair[1];
            }
        }
        return "";
    }

    private static void cookie(HttpExchange exchange, String token, long seconds) {
        String secure = Boolean.parseBoolean(System.getenv("PANNED_OUT_SECURE_COOKIES")) ? "; Secure" : "";
        exchange.getResponseHeaders().add("Set-Cookie", COOKIE + "=" + token
                + "; Path=/api; HttpOnly; SameSite=Strict; Max-Age=" + seconds + secure);
    }

    private static String json(AccountRepository.Account account) {
        return "{\"id\":" + RecipeServer.quote(account.id) + ",\"email\":" + RecipeServer.quote(account.email) + "}";
    }
}
