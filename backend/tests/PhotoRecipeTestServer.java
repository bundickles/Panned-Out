import com.sun.net.httpserver.HttpServer;
import java.awt.image.BufferedImage;
import java.net.URI;
import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.ExecutorService;
import javax.imageio.ImageIO;

/** Test-only entry point: a local fake provider, isolated storage, and no real API key. */
public final class PhotoRecipeTestServer {
    public static void main(String[] args) throws Exception {
        if (args.length == 2 && args[0].equals("--write-test-jpeg")) {
            ImageIO.write(new BufferedImage(3, 2, BufferedImage.TYPE_INT_RGB),
                    "jpeg", Path.of(args[1]).toFile());
            return;
        }
        if (args.length < 2)
            throw new IllegalArgumentException("Expected storage path and local provider endpoint or --configured");
        PhotoRecipeApi api;
        if (args[1].equals("--configured")) {
            api = PhotoRecipeApi.fromEnvironment();
        } else {
            String key = args.length > 2 ? args[2] : "photo-test-key";
            long timeoutMs = args.length > 3 ? Long.parseLong(args[3]) : 5000;
            api = new PhotoRecipeApi(new OpenAiPhotoRecipeClient(
                    key, "test-vision-model", URI.create(args[1]), Duration.ofMillis(timeoutMs)));
        }
        HttpServer server = RecipeServer.startServer(0, Path.of(args[0]), api);
        System.out.println("Recipe API: http://127.0.0.1:" + server.getAddress().getPort());
        System.out.flush();
        // Graceful shutdown also works when Windows java.exe is a launcher process.
        try {
            System.in.read();
        } finally {
            server.stop(0);
            ((ExecutorService) server.getExecutor()).shutdownNow();
        }
    }
}
