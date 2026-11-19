
import "./MealCard.css";

export default function MealCard({
  meal,
  variant = "compact",
}) {
  const difficulty = String(
    meal.difficulty || "Medium"
  ).trim().toLowerCase();

  const difficultyClass = ["easy", "medium", "hard"]
    .includes(difficulty)
    ? difficulty
    : "medium";

  const mealType = meal.type || meal.mealType || "Meal";

  return (
    <article
      className={`meal-card meal-card--${variant} difficulty-${difficultyClass}`}
    >
      {/* Meal photo */}
      <div className="meal-card-image">
        {meal.image ? (
          <img src={meal.image} alt="" loading="lazy" />
        ) : (
          <div className="meal-card-image-placeholder">
            <span aria-hidden="true">✿</span>
          </div>
        )}
      </div>

      {/* Meal information */}
      <div className="meal-card-body">
        <div className="meal-card-header">
          <span className="meal-type">{mealType}</span>

          <span className="meal-difficulty">
            <span className="meal-difficulty-dot" />
            {meal.difficulty || "Medium"}
          </span>
        </div>

        <h3>{meal.name}</h3>

        <div className="meal-info">
          {meal.prepTime != null && (
            <span>⏱ {meal.prepTime} min</span>
          )}

          {meal.nutritionAvailable && (
            <span>
              {Math.round(Number(meal.calories))} cal
            </span>
          )}

          {meal.servings != null && (
            <span>{meal.servings} servings</span>
          )}
        </div>
      </div>
    </article>
  );
}
