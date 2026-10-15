import "./MealCard.css";

function MealCard({meal, onClick }) {

    // Gets difficulty and converts it to lowercase
    const difficulty = String(meal.difficulty || "Medium")
        .trim()
        .toLowerCase();

    // Chooses CSS class based on difficulty
    const difficultyClass = ["easy", "medium", "hard"].includes(difficulty)
        ? ` difficulty-${difficulty}`
        : " difficulty-medium";

    return (
        <article
        className={`meal-card${difficultyClass}`}
        onClick={onClick}
        >
            <div className="meal-card-header">
                <span className="meal-type">
                    {meal.type}
                </span>

                <span className="meal-difficulty">
                    {meal.difficulty}
                </span>
            </div>

            <h3>{meal.name}</h3>

            <div className="meal-info">
                <span>
                    ⏱ {meal.prepTime}
                </span>

                <span>
                    🍽 {meal.servings} servings
                </span>
            </div>
        </article>
    );
}

export default MealCard;