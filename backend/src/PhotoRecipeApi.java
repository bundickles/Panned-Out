import com.sun.net.httpserver.HttpExchange;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Semaphore;
import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.MemoryCacheImageInputStream;

/** Generates a preview only. Neither uploads nor generated recipes are written to storage. */
final class PhotoRecipeApi {
    static final int MAX_IMAGE_BYTES = 5 * 1024 * 1024;
    private static final long MAX_PIXELS = 16_000_000;
    private static final long WINDOW_MS = 60_000;
    private static final int REQUESTS_PER_MINUTE = 6;
    private final Generator generator;
    private final Semaphore activeRequests = new Semaphore(2);
    private final Map<String, Window> attempts = new HashMap<>();

    @FunctionalInterface
    interface Generator {
        String generate(byte[] image, String mimeType);

        default boolean isDemo() { return false; }
    }

    private static final class Window {
        final long expires;
        int count;
        Window(long expires) { this.expires = expires; }
    }

    PhotoRecipeApi(Generator generator) {
        this.generator = generator;
    }

    /** Local demo is the default. Paid provider use requires an explicit server setting. */
    static PhotoRecipeApi fromEnvironment() {
        String mode = System.getenv("PANNED_OUT_AI_MODE");
        mode = mode == null || mode.trim().isEmpty() ? "demo" : mode.trim().toLowerCase(Locale.ROOT);
        if (mode.equals("demo"))
            return new PhotoRecipeApi(new DemoPhotoRecipeGenerator(System.getenv("PANNED_OUT_AI_DEMO_RESULT")));
        if (mode.equals("openai"))
            return new PhotoRecipeApi(new OpenAiPhotoRecipeClient());
        throw new IllegalArgumentException("PANNED_OUT_AI_MODE must be demo or openai.");
    }

    boolean isDemo() { return generator.isDemo(); }

    void handle(HttpExchange exchange, String accountId) throws IOException {
        if (isDemo()) exchange.getResponseHeaders().set("X-Panned-Out-AI-Mode", "demo");
        if (!exchange.getRequestMethod().equals("POST")) {
            exchange.getResponseHeaders().set("Allow", "POST");
            throw new RecipeServer.ApiError(405, "Method not allowed.");
        }
        String type = exchange.getRequestHeaders().getFirst("Content-Type");
        type = type == null ? "" : type.split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
        if (!type.equals("image/jpeg") && !type.equals("image/png"))
            throw new RecipeServer.ApiError(415, "Upload a JPEG or PNG file as the request body.");
        String encoding = exchange.getRequestHeaders().getFirst("Content-Encoding");
        if (encoding != null && !encoding.equalsIgnoreCase("identity"))
            throw new RecipeServer.ApiError(415, "Compressed request bodies are not supported.");
        String length = exchange.getRequestHeaders().getFirst("Content-Length");
        if (length != null) {
            try {
                long size = Long.parseLong(length);
                if (size < 0) throw new NumberFormatException();
                if (size > MAX_IMAGE_BYTES)
                    throw new RecipeServer.ApiError(413, "Image must be 5 MiB or smaller.");
            } catch (NumberFormatException e) {
                throw new RecipeServer.ApiError(400, "Invalid upload length.");
            }
        }
        if (!activeRequests.tryAcquire()) {
            exchange.getResponseHeaders().set("Retry-After", "2");
            throw new RecipeServer.ApiError(429, "Photo generation is busy. Please try again shortly.");
        }
        try {
            byte[] image = exchange.getRequestBody().readNBytes(MAX_IMAGE_BYTES + 1);
            if (image.length > MAX_IMAGE_BYTES)
                throw new RecipeServer.ApiError(413, "Image must be 5 MiB or smaller.");
            validateImage(image, type);
            throttle(exchange, accountId);
            RecipeServer.respond(exchange, 200, generator.generate(image, type));
        } finally {
            activeRequests.release();
        }
    }

    private static void validateImage(byte[] image, String mimeType) {
        if (image.length == 0) throw new RecipeServer.ApiError(400, "Choose an image to upload.");
        // Use a memory stream explicitly so ImageIO does not cache private uploads on disk.
        try (MemoryCacheImageInputStream input = new MemoryCacheImageInputStream(new ByteArrayInputStream(image))) {
            Iterator<ImageReader> readers = ImageIO.getImageReaders(input);
            if (!readers.hasNext()) throw new RecipeServer.ApiError(400, "The image is invalid or damaged.");
            ImageReader reader = readers.next();
            try {
                String format = reader.getFormatName().toLowerCase(Locale.ROOT);
                if (!(mimeType.equals("image/png") && format.equals("png"))
                        && !(mimeType.equals("image/jpeg") && (format.equals("jpeg") || format.equals("jpg"))))
                    throw new RecipeServer.ApiError(415, "Image content does not match its JPEG or PNG type.");
                reader.setInput(input, true, true);
                int width = reader.getWidth(0), height = reader.getHeight(0);
                if (width <= 0 || height <= 0 || width > 8192 || height > 8192
                        || (long) width * height > MAX_PIXELS)
                    throw new RecipeServer.ApiError(413, "Image dimensions are too large. Resize it to 16 megapixels or less.");
                if (reader.read(0) == null)
                    throw new RecipeServer.ApiError(400, "The image is invalid or damaged.");
            } finally {
                reader.dispose();
            }
        } catch (IOException | IllegalArgumentException e) {
            throw new RecipeServer.ApiError(400, "The image is invalid or damaged.");
        }
    }

    private synchronized void throttle(HttpExchange exchange, String accountId) {
        long now = System.currentTimeMillis();
        attempts.values().removeIf(window -> window.expires <= now);
        Window window = attempts.computeIfAbsent(accountId, ignored -> new Window(now + WINDOW_MS));
        if (window.count >= REQUESTS_PER_MINUTE) {
            exchange.getResponseHeaders().set("Retry-After", Long.toString((window.expires - now + 999) / 1000));
            throw new RecipeServer.ApiError(429, "Limit of six photo requests per minute. Please try again later.");
        }
        window.count++;
    }
}
