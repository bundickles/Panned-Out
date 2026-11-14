
import "./RecipeCard.css";

export default function RecipeCard({
  recipe,
  onClick,
  onEdit,
  onDelete,
  deleting = false,
}) {
  const difficulty = String(
    recipe.difficulty || "Medium"
  ).trim().toLowerCase();

  const difficultyClass = ["easy", "medium", "hard"]
    .includes(difficulty)
    ? difficulty
    : "medium";

  return (
    <article className={`recipe-card difficulty-${difficultyClass}`}>
      <button
        type="button"
        className="recipe-card-open"
        onClick={onClick}
        aria-label={`Open recipe: ${recipe.name}`}
      >
        {/* Recipe photo */}
        <div className="recipe-image">
          {recipe.image ? (
            <img src={recipe.image} alt="" loading="lazy" />
          ) : (
            <div className="recipe-image-placeholder">
              <span aria-hidden="true">✿</span>
              <small>FROM YOUR KITCHEN</small>
            </div>
          )}

          <span className="recipe-photo-label">
            {recipe.mealType || "Recipe"}
          </span>
        </div>

        {/* Recipe details */}
        <div className="recipe-card-content">
          <div className="recipe-card-top">
            <span className="recipe-category">
              {recipe.category || "My Recipes"}
            </span>

            <span className="recipe-difficulty">
              <span
                className="recipe-difficulty-dot"
                aria-hidden="true"
              />
              {recipe.difficulty || "Medium"}
            </span>
          </div>

          <h3>{recipe.name}</h3>

          <div className="recipe-details">
            <span>
              {recipe.prepTime != null
                ? `${recipe.prepTime} min`
                : "Time unavailable"}
            </span>

            {recipe.calories != null && (
              <span>{recipe.calories} cal</span>
            )}
          </div>

          <span className="recipe-card-link">
            View recipe <span aria-hidden="true">→</span>
          </span>
        </div>
      </button>

      {/* Separate controls prevent accidental navigation */}
      <div className="recipe-card-actions">
        <button
          type="button"
          className="recipe-edit"
          disabled={deleting}
          onClick={() => onEdit(recipe)}
        >
          Edit recipe
        </button>

        <button
          type="button"
          className="recipe-delete"
          disabled={deleting}
          onClick={() => onDelete(recipe.id)}
          aria-label={`Delete ${recipe.name}`}
        >
          Delete
        </button>
      </div>
    </article>
  );
}
