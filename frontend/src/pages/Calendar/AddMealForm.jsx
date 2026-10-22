import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getRecipes } from '../../api/recipes';

export default function AddMealForm({ date, onSave, onCancel }) {
    const [recipes, setRecipes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [loadError, setLoadError] = useState('');
    const [saveError, setSaveError] = useState('');
    const [revision, setRevision] = useState(0);

    useEffect(() => {
        let active = true;
        getRecipes().then(data => { if (active) setRecipes(data); })
            .catch(error => { if (active) setLoadError(error.message); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [revision]);

    async function submit(event) {
        event.preventDefault();
        const fields = Object.fromEntries(new FormData(event.currentTarget));
        setSaving(true);
        setSaveError('');
        try { await onSave({ ...fields, date }); }
        catch (error) { setSaveError(error.message); }
        finally { setSaving(false); }
    }

    return <form className="add-meal-form" onSubmit={submit} aria-labelledby="add-meal-title">
        <h3 id="add-meal-title">Add a meal for {date}</h3>
        {loading ? <p role="status">Loading your recipes...</p> : loadError ?
            <div role="alert">{loadError} <button type="button" onClick={() => {
                setLoading(true); setLoadError(''); setRevision(value => value + 1);
            }}>Retry recipes</button></div> : recipes.length === 0 ?
                <p>You have no saved recipes yet. <Link to="/recipes">Create a recipe</Link>, then return to add it to your calendar.</p> :
                <fieldset disabled={saving}>
                    <label htmlFor="meal-recipe">Recipe</label>
                    <select id="meal-recipe" name="recipeId" defaultValue="" required>
                        <option value="" disabled>Choose a recipe</option>
                        {recipes.map(recipe => <option key={recipe.id} value={recipe.id}>{recipe.name}</option>)}
                    </select>
                    <label htmlFor="scheduled-meal-type">Meal type</label>
                    <select id="scheduled-meal-type" name="mealType" defaultValue="Dinner">
                        {['Breakfast', 'Lunch', 'Dinner', 'Snack'].map(type => <option key={type}>{type}</option>)}
                    </select>
                    <button className="add-meal-button" type="submit">{saving ? 'Saving...' : 'Save meal'}</button>
                </fieldset>}
        {saveError && <p role="alert">{saveError}</p>}
        <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
    </form>;
}
