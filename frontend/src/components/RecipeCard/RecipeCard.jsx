import './RecipeCard.css';

function RecipeCard({ recipe, onDelete }) {
    return (
        <article className="recipe-card">

            <div className="recipe-image">
                {recipe.image ? (
                    <img src={recipe.image} alt={recipe.name} />
                ) : (
                    <span>🍽</span>
                )}
            </div>

            <div className="recipe-card-content">

                <div className="recipe-card-top">
                    <span className="recipe-category">
                        {recipe.category}
                    </span>

                    <button
                        className="recipe-delete"
                        onClick={() => onDelete(recipe.id)}
                        aria-label={`Delete ${recipe.name}`}
                    >
                        🗑
                    </button>

                </div>

                <h3>{recipe.name}</h3>

                <div className="recipe-details">

                    <span>{recipe.difficulty}</span>
                    <span>{recipe.prepTime} mins</span>
                </div>

                <div className="recipe-nutrition">

                    <span>{recipe.calories} cal</span>
                    <span>{recipe.protein} g protein</span>
                    <span>{recipe.fat} g fat</span>
                    <span>{recipe.carbohydrates} g carbs</span>
                    <span>{recipe.fiber} g fiber</span>

                </div>
            </div>
        </article>
    );
}

export default RecipeCard;