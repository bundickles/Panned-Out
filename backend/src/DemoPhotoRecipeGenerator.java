import java.util.Locale;

/** Fixed local fixtures for presentations. No image recognition, network, or storage access. */
final class DemoPhotoRecipeGenerator implements PhotoRecipeApi.Generator {
    private final String result;

    DemoPhotoRecipeGenerator(String result) {
        this.result = result == null || result.trim().isEmpty()
                ? "recipe" : result.trim().toLowerCase(Locale.ROOT);
        if (!java.util.List.of("recipe", "no_result", "error").contains(this.result))
            throw new IllegalArgumentException("PANNED_OUT_AI_DEMO_RESULT must be recipe, no_result, or error.");
    }

    @Override public boolean isDemo() { return true; }

    @Override public String generate(byte[] image, String mimeType) {
        if (result.equals("error"))
            throw new RecipeServer.ApiError(502,
                    "Demo mode: simulated generation failure. No AI service was contacted.");
        if (result.equals("no_result"))
            return "{\"demo\":true,\"status\":\"no_result\",\"recipe\":null,\"message\":"
                    + RecipeServer.quote("Demo mode: simulated no-result response. This photo was not analyzed.") + "}";
        return "{\"demo\":true,\"status\":\"recipe\",\"message\":"
                + RecipeServer.quote("Demo mode: this is a fixed sample recipe. Your photo was not analyzed.")
                + ",\"recipe\":{\"name\":\"Demo vegetable rice bowl\",\"ingredients\":"
                + RecipeServer.quote("1 cup rice\n2 cups water\n1 carrot, diced\n1 cup frozen peas\n1 tablespoon olive oil")
                + ",\"instructions\":"
                + RecipeServer.quote("1. Cook the rice with the water according to its package directions.\n"
                        + "2. Heat the olive oil in a pan and cook the carrot until tender.\n"
                        + "3. Add the peas and cook until heated through.\n"
                        + "4. Serve the vegetables over the rice.") + "}}";
    }
}
