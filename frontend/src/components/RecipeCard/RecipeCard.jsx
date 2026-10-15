
import "./RecipeCard.css";

function RecipeCard({ recipe, onClick, onDelete, deleting }) {
    const difficulty = String(recipe.difficulty || "Medium")
        .trim()
        .toLowerCase();

    const difficultyClass = ["easy", "medium", "hard"].includes(difficulty)
        ? `difficulty-${difficulty}`
        : "difficulty-medium";

    return (
        <article
            className={`recipe-card ${difficultyClass}`}
        >
            <button
                type="button"
                className="recipe-card-open"
                onClick={onClick}
                aria-label={`Open recipe: ${recipe.name}`}
            >
                <div className="recipe-image">
                    {recipe.image ? (
                        <img src={recipe.image} alt={recipe.name} />
                    ) : (
                        <span aria-hidden="true">🍲</span>
                    )}
                </div>

                <div className="recipe-card-content">
                    <div className="recipe-card-top">
                        <span className="recipe-category">
                            {recipe.category || "My Recipes"}
                        </span>

                        <span className="recipe-difficulty">
                            {recipe.difficulty || "Medium"}
                        </span>
                    </div>

                    <h3>{recipe.name}</h3>

                    <div className="recipe-details">
                        <span>{recipe.prepTime} min</span>
                        <span>{recipe.mealType || "Recipe"}</span>
                    </div>

                    <span className="recipe-card-link">
                        Open recipe →
                    </span>
                </div>
            </button>

            <button
                type="button"
                className="recipe-delete"
                disabled={deleting}
                onClick={() => onDelete(recipe.id)}
                aria-label={`Delete ${recipe.name}`}
            >
                🗑
            </button>
        </article>
    );
}

export default RecipeCard;
