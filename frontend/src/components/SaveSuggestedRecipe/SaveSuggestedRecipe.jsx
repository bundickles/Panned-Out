import { useState } from 'react';
import { saveSuggestedRecipe } from '../../api/recipes';
import './SaveSuggestedRecipe.css';

export default function SaveSuggestedRecipe({ recipe, savedId, checking }) {
    const [choosing, setChoosing] = useState(false);
    const [mealType, setMealType] = useState('Dinner');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [saved, setSaved] = useState(false);
    async function submit(event) {
        event.preventDefault(); setBusy(true); setError('');
        try {
            await saveSuggestedRecipe(recipe.id, mealType);
            setSaved(true); setChoosing(false);
            window.dispatchEvent(new Event('panned-suggestion-saved'));
        } catch (error) { setError(error.message); }
        finally { setBusy(false); }
    }
    if (recipe.source !== 'suggested') return null;
    return <div className="save-suggestion">
        {savedId || saved ? <button type="button" disabled aria-label={`${recipe.name} saved to My Recipes`}>Saved to My Recipes</button>
            : choosing ? <form onSubmit={submit} aria-label={`Save ${recipe.name}`}>
                <label>Meal type<select aria-label={`Meal type for ${recipe.name}`} value={mealType} onChange={event => setMealType(event.target.value)} disabled={busy}>
                    {['Breakfast', 'Lunch', 'Dinner', 'Snack'].map(type => <option key={type}>{type}</option>)}
                </select></label>
                <button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save recipe'}</button>
                <button type="button" disabled={busy} onClick={() => {setChoosing(false);setError('');}}>Cancel</button>
            </form> : <button type="button" disabled={checking} onClick={() => setChoosing(true)} aria-label={`Save ${recipe.name} to My Recipes`}>Save to My Recipes</button>}
        {error && <p role="alert">{error} Try saving again.</p>}
    </div>;
}
