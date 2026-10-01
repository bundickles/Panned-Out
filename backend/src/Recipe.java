public class Recipe {

    private int id;
    private String name;
    private String category;
    private String difficulty;
    private int prepTime;
    private int calories;
    private int protein;
    private int fat;
    private int carbohydrates;
    private int fiber;
    private String image;
    private String ingredients;
    private String instructions;
    private String mealType;

    public Recipe(int id, String name, String category, String difficulty,
                  int prepTime, int calories, int protein, int fat,
                  int carbohydrates, int fiber, String image) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.difficulty = difficulty;
        this.prepTime = prepTime;
        this.calories = calories;
        this.protein = protein;
        this.fat = fat;
        this.carbohydrates = carbohydrates;
        this.fiber = fiber;
        this.image = image;
    }

    public Recipe(int id, String name, String ingredients, String instructions, String mealType) {
        this.id = id;
        this.name = name;
        this.ingredients = ingredients;
        this.instructions = instructions;
        this.mealType = mealType;
    }

    // Used by storage to restore both recipe details and existing meal-card fields.
    Recipe(int id, String name, String category, String difficulty,
           int prepTime, int calories, int protein, int fat,
           int carbohydrates, int fiber, String image,
           String ingredients, String instructions, String mealType) {
        this(id, name, category, difficulty, prepTime, calories, protein, fat,
                carbohydrates, fiber, image);
        this.ingredients = ingredients;
        this.instructions = instructions;
        this.mealType = mealType;
    }

    public int getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getCategory() {
        return category;
    }

    public String getDifficulty() {
        return difficulty;
    }

    public int getPrepTime() {
        return prepTime;
    }

    public int getCalories() {
        return calories;
    }

    public int getProtein() {
        return protein;
    }

    public int getFat() {
        return fat;
    }

    public int getCarbohydrates() {
        return carbohydrates;
    }

    public int getFiber() {
        return fiber;
    }

    public String getImage() {
        return image;
    }

    public String getIngredients() {
        return ingredients;
    }

    public String getInstructions() {
        return instructions;
    }

    public String getMealType() {
        return mealType;
    }
}
