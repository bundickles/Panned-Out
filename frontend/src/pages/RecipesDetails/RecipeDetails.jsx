import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRecipes } from "../../api/recipes";
import "./RecipeDetails.css";


function RecipeDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [recipe, setRecipe] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [checkedIngredients, setCheckedIngredients] = useState([]);

    useEffect(() => {
        let active = true;

        async function loadRecipe() {
            setLoading(true);
            setError("");

            try {
                const recipes = await getRecipes();
                const found = recipes.find(
                    (item) => String(item.id) === id
                );

                if (!active) return;

                if (found) {
                    setRecipe(found);
                } else {
                    setError("Recipe not found");
                }

            } catch (err) {
                if (active) {
                    setError(err.message || "An error occurred");
                }
            } finally {
                if (active) {
                    setLoading(false);
                }
            }
        }

        loadRecipe();

        return () => {
            active = false;
        };
    }, [id]);

    if (loading) {
        return (
            <main className="recipe-detal-page">
                <p role="status">Opening your recipe...</p>
            </main>
        );
    }

    if (error || !recipe) {
        return (
            <main className="recipe-detal-page">
                <button
                    className="journal-back"
                    onClick={() => navigate("/recipes")}
                >
                    ← Back to Recipes
                </button>
                
                <div className="journal-message">
                    <h1>Recipe not found</h1>
                    <p>
                        {error || "The recipe you are looking for does not exist."}
                    </p>
                </div>
            </main>
        );
    }

    const difficulty = String(recipe.difficulty || "Medium")
        .trim().toLowerCase();
    
    const difficultyClass = ["easy", "medium", "hard"].includes(difficulty)
        ? `difficulty-${difficulty}`
        : "difficulty-medium";
    const ingredients = String(recipe.ingredients || "")
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean);

    const instructions = String(recipe.instructions || "")
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean);

    function toggleIngredient(index) {
        setCheckedIngredients((current) =>
            current.includes(index)
                ? current.filter((item) => item !== index)
                : [...current, index]
        );
    }

    function addToShoppingList() {
        // Navigation only for now. We will connect the
        // selected recipe's ingredients to shared shopping-list
        // data when that page is implemented.
        navigate("/shopping");
    }

    function addToCalendar() {
        // Opens the calendar for now. Saving a scheduled meal
        // requires connecting this action to calendar data.
        navigate("/calendar");
    }

    //existing form doesn't collect servings or a description, so the page uses a placeholder for servings and a short 
    //decorative sentence for the description.

    return (
        <main className={`recipe-detail-page ${difficultyClass}`}>
            <header className="journal-topbar">
                <button
                    className="journal-back"
                    onClick={() => navigate("/recipes")}
                >
                    ← Back to Recipes
                </button>

                <span className="journal-brand">Panned Out</span>
            </header>

            <article className="journal-paper">
                {/* Recipe photo and introduction */}
                <section className="journal-hero">
                    <div className="journal-photo-frame">
                        {recipe.image ? (
                            <img
                                className="journal-photo"
                                src={recipe.image}
                                alt={recipe.name}
                            />
                        ) : (
                            <div className="journal-photo-placeholder">
                                <span aria-hidden="true">🍲</span>
                                <p>A recipe worth keeping</p>
                            </div>
                        )}

                        <p className="journal-photo-caption">
                            From my recipe collection
                        </p>
                    </div>

                    <div className="journal-intro">
                        <p className="journal-eyebrow">
                            {recipe.mealType || "RECIPE"}{" "}
                            <span>·</span>{" "}
                            {recipe.category || "MY COLLECTION"}
                        </p>

                        <h1>{recipe.name}</h1>

                        <p className="journal-description">
                            A favorite to make, share, and come back to.
                        </p>

                        <span className="journal-difficulty">
                            <span className="difficulty-dot" />
                            {recipe.difficulty || "Medium"} difficulty
                        </span>

                        <div className="journal-stats">
                            <div>
                                <span>PREP TIME</span>
                                <strong>
                                    {recipe.prepTime ?? "—"} min
                                </strong>
                            </div>

                            <div>
                                <span>SERVINGS</span>
                                <strong>
                                    {recipe.servings ?? "—"}
                                </strong>
                            </div>

                            <div>
                                <span>CALORIES</span>
                                <strong>
                                    {recipe.calories ?? "—"}
                                </strong>
                            </div>
                        </div>

                        <div className="journal-actions">
                            <button
                                className="journal-primary-button"
                                onClick={addToCalendar}
                            >
                                + Add to Calendar
                            </button>

                            <button
                                className="journal-secondary-button"
                                onClick={addToShoppingList}
                            >
                                + Shopping List
                            </button>
                        </div>

                        <p className="journal-handwritten">
                            Made with care, saved for another day.
                        </p>
                    </div>
                </section>

                <div className="journal-divider">
                    <span>✳</span>
                </div>

                {/* Ingredients and instructions */}
                <div className="journal-body">
                    <section className="journal-section">
                        <header className="journal-section-heading">
                            <span>GATHER YOUR INGREDIENTS</span>
                            <h2>Ingredients</h2>
                            <p>Check off each item as you prepare.</p>
                        </header>

                        {ingredients.length > 0 ? (
                            <ul className="journal-ingredients">
                                {ingredients.map((ingredient, index) => (
                                    <li key={`${index}-${ingredient}`}>
                                        <label
                                            className={
                                                checkedIngredients.includes(index)
                                                    ? "ingredient-checked"
                                                    : ""
                                            }
                                        >
                                            <input
                                                type="checkbox"
                                                checked={checkedIngredients.includes(index)}
                                                onChange={() =>
                                                    toggleIngredient(index)
                                                }
                                            />

                                            <span>{ingredient}</span>
                                        </label>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p>No ingredients have been added yet.</p>
                        )}

                        <button
                            className="journal-text-button"
                            onClick={addToShoppingList}
                        >
                            Add ingredients to shopping list →
                        </button>
                    </section>

                    <section className="journal-section">
                        <header className="journal-section-heading">
                            <span>TAKE IT STEP BY STEP</span>
                            <h2>Instructions</h2>
                            <p>There's no rush. Enjoy the process.</p>
                        </header>

                        {instructions.length > 0 ? (
                            <ol className="journal-instructions">
                                {instructions.map((instruction, index) => (
                                    <li key={`${index}-${instruction}`}>
                                        <span className="instruction-number">
                                            {index + 1}
                                        </span>

                                        <p>{instruction}</p>
                                    </li>
                                ))}
                            </ol>
                        ) : (
                            <p>No instructions have been added yet.</p>
                        )}
                    </section>
                </div>

                {/* Nutrition */}
                <section className="journal-nutrition">
                    <div className="journal-nutrition-heading">
                        <span>NUTRITION AT A GLANCE</span>
                        <h2>A little nourishment</h2>
                    </div>

                    <div className="nutrition-values">
                        <div>
                            <strong>{recipe.calories ?? "—"}</strong>
                            <span>Calories</span>
                        </div>
                        <div>
                            <strong>{recipe.protein ?? "—"} g</strong>
                            <span>Protein</span>
                        </div>
                        <div>
                            <strong>{recipe.fat ?? "—"} g</strong>
                            <span>Fat</span>
                        </div>
                        <div>
                            <strong>{recipe.carbohydrates ?? "—"} g</strong>
                            <span>Carbs</span>
                        </div>
                        <div>
                            <strong>{recipe.fiber ?? "—"} g</strong>
                            <span>Fiber</span>
                        </div>
                    </div>
                </section>

                <footer className="journal-footer">
                    <span>✿</span>
                    Good food brings people together.
                    <span>✿</span>
                </footer>
            </article>
        </main>
    );
}

export default RecipeDetails;