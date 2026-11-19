import com.sun.net.httpserver.HttpExchange;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.*;
import java.util.Iterator;
import java.util.Locale;
import java.util.concurrent.Semaphore;
import javax.imageio.*;
import javax.imageio.stream.MemoryCacheImageInputStream;

/** SCRUM-139: validates an upload and returns a draft; never accesses recipe storage. */
final class AiPhotoApi {
    static final int MAX_BYTES = 5 * 1024 * 1024;
    static final long MAX_PIXELS = 16000000;
    interface Generator {
        boolean available();
        String generate(byte[] jpeg);
    }
    private final Generator generator;
    private final Semaphore slots = new Semaphore(2);
    private long windowStart;
    private int attempts;

    AiPhotoApi(Generator generator) { this.generator = generator; }

    private synchronized void reserve() {
        long now = System.nanoTime();
        if (now - windowStart >= 60_000_000_000L || windowStart == 0) { windowStart = now; attempts = 0; }
        if (attempts >= 6) throw new RecipeServer.ApiError(429, "Photo analysis is busy. Please wait a minute and try again.");
        attempts++;
    }

    void handle(HttpExchange exchange) throws IOException {
        String method = exchange.getRequestMethod();
        if (method.equals("GET")) {
            RecipeServer.respond(exchange, 200, "{\"available\":" + generator.available()
                + ",\"maxBytes\":" + MAX_BYTES + ",\"acceptedTypes\":[\"image/jpeg\",\"image/png\"]}");
            return;
        }
        if (!method.equals("POST")) {
            exchange.getResponseHeaders().set("Allow", "GET, POST");
            throw new RecipeServer.ApiError(405, "Use POST to upload a JPEG or PNG photo.");
        }
        String type = exchange.getRequestHeaders().getFirst("Content-Type");
        type = type == null ? "" : type.split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
        if (!type.equals("image/jpeg") && !type.equals("image/png"))
            throw new RecipeServer.ApiError(415, "Upload a JPEG or PNG photo as the request body.");
        String length = exchange.getRequestHeaders().getFirst("Content-Length");
        if (length != null) {
            try { if (Long.parseLong(length) > MAX_BYTES) throw new RecipeServer.ApiError(413, "Photo must be 5 MiB or smaller."); }
            catch (NumberFormatException e) { throw new RecipeServer.ApiError(400, "Invalid upload length."); }
        }
        if (!slots.tryAcquire()) throw new RecipeServer.ApiError(429, "Two photos are already being analyzed. Please try again shortly.");
        try {
            byte[] bytes = exchange.getRequestBody().readNBytes(MAX_BYTES + 1);
            if (bytes.length > MAX_BYTES) throw new RecipeServer.ApiError(413, "Photo must be 5 MiB or smaller.");
            byte[] jpeg = normalize(bytes, type);
            if (!generator.available()) throw new RecipeServer.ApiError(503, "AI photo analysis is not configured yet.");
            reserve();
            RecipeServer.respond(exchange, 200, generator.generate(jpeg));
        } finally { slots.release(); }
    }

    static byte[] normalize(byte[] bytes, String type) {
        if (bytes.length == 0) throw new RecipeServer.ApiError(400, "Choose a photo before uploading.");
        try (MemoryCacheImageInputStream input = new MemoryCacheImageInputStream(new ByteArrayInputStream(bytes))) {
            Iterator<ImageReader> readers = ImageIO.getImageReaders(input);
            if (!readers.hasNext()) throw new IOException("Unrecognized image");
            ImageReader reader = readers.next();
            try {
                String format = reader.getFormatName();
                if (!(type.equals("image/jpeg") && format.equalsIgnoreCase("JPEG"))
                        && !(type.equals("image/png") && format.equalsIgnoreCase("PNG")))
                    throw new RecipeServer.ApiError(415, "Photo contents do not match its JPEG or PNG file type.");
                reader.setInput(input, true, true);
                int width = reader.getWidth(0), height = reader.getHeight(0);
                if (width <= 0 || height <= 0 || (long) width * height > MAX_PIXELS)
                    throw new RecipeServer.ApiError(413, "Photo must be 16 megapixels or smaller.");
                ImageReadParam params = reader.getDefaultReadParam();
                int sample = Math.max(1, (Math.max(width, height) + 1023) / 1024);
                params.setSourceSubsampling(sample, sample, 0, 0);
                BufferedImage decoded = reader.read(0, params);
                if (decoded == null) throw new IOException("Cannot decode image");
                BufferedImage clean = new BufferedImage(decoded.getWidth(), decoded.getHeight(), BufferedImage.TYPE_INT_RGB);
                Graphics2D graphics = clean.createGraphics();
                try {
                    graphics.setColor(Color.WHITE);
                    graphics.fillRect(0, 0, clean.getWidth(), clean.getHeight());
                    graphics.drawImage(decoded, 0, 0, null);
                } finally { graphics.dispose(); }
                ByteArrayOutputStream output = new ByteArrayOutputStream();
                // Re-encoding removes EXIF/location and other metadata; no file is written.
                if (!ImageIO.write(clean, "jpeg", output)) throw new IOException("JPEG writer unavailable");
                return output.toByteArray();
            } finally { reader.dispose(); }
        } catch (IOException | IllegalArgumentException e) {
            throw new RecipeServer.ApiError(400, "The photo is damaged or unreadable. Try another JPEG or PNG.");
        }
    }
}
