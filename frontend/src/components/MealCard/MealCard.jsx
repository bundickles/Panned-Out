import "./MealCard.css";

function MealCard({
    meal,
    onClick
}) {
    return (
        <article
        className="meal-card"
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
                    ⏱ {meal.prepTime} min
                </span>

                {meal.servings != null && <span>
                    🍽 {meal.servings} servings
                </span>}
            </div>
        </article>
    );
}

export default MealCard;
