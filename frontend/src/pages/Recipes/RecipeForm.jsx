import { useState } from 'react';

export default function RecipeForm({ recipe, onSave, onCancel }) {
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    async function submit(event) {
        event.preventDefault();
        const fields = Object.fromEntries(new FormData(event.currentTarget));
        setSaving(true);
        setError('');
        try {
            await onSave(fields);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    }
    return (
        <form className="recipe-form" onSubmit={submit} aria-labelledby="recipe-form-title">
            <h2 id="recipe-form-title">{recipe ? 'Edit Recipe' : 'Add Recipe'}</h2>
            <fieldset disabled={saving}>
                <label>Recipe name<input name="name" defaultValue={recipe?.name ?? ""} required maxLength={200} autoFocus /></label>
                <label>Category<select name="category" defaultValue={recipe?.category ?? "My Recipes"}>
                    {['My Recipes', 'High Protein', 'Low Calorie', 'Keto'].map(value => <option key={value}>{value}</option>)}
                </select></label>
                <label>Difficulty<select name="difficulty" defaultValue={recipe?.difficulty ?? "Easy"}>
                    {['Easy', 'Medium', 'Hard'].map(value => <option key={value}>{value}</option>)}
                </select></label>
                <label>Meal type<select name="mealType" defaultValue={recipe?.mealType ?? "Breakfast"}>
                    {['Breakfast', 'Lunch', 'Dinner', 'Snack'].map(value => <option key={value}>{value}</option>)}
                </select></label>
                <label>Ingredients<textarea name="ingredients" defaultValue={recipe?.ingredients ?? ""} required maxLength={10000} rows={3} /></label>
                <label>Instructions<textarea name="instructions" defaultValue={recipe?.instructions ?? ""} required maxLength={10000} rows={3} /></label>
                <div className="recipe-form-numbers">
                    {[['prepTime', 'Prep time (minutes)'], ['calories', 'Calories'], ['protein', 'Protein (g)'],
                        ['fat', 'Fat (g)'], ['carbohydrates', 'Carbohydrates (g)'], ['fiber', 'Fiber (g)']].map(([name, label]) => (
                        <label key={name}>{label}<input name={name} type="number" min="0" max="100000" step="1" defaultValue={recipe?.[name] ?? 0} required /></label>
                    ))}
                </div>
                <button className="add-recipe-button" type="submit">{saving ? 'Saving…' : 'Save recipe'}</button>
                <button type="button" onClick={onCancel}>Cancel</button>
            </fieldset>
            {error && <p role="alert">{error}</p>}
        </form>
    );
}
