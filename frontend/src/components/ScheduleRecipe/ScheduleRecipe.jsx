import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { addMeal } from '../../api/meals';
import { saveSuggestedRecipe } from '../../api/recipes';
import { validateRange } from '../../api/shopping';
import './ScheduleRecipe.css';

export default function ScheduleRecipe({ recipe, onCancel }) {
    const navigate = useNavigate();
    const today = new Date();
    const [date, setDate] = useState(`${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`);
    const [mealType, setMealType] = useState(recipe.mealType || 'Dinner');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [privateId, setPrivateId] = useState(recipe.source === 'suggested' ? null : recipe.id);
    async function submit(event) {
        event.preventDefault(); setError('');
        if (validateRange(date,date) || !['Breakfast','Lunch','Dinner','Snack'].includes(mealType)) {
            setError('Choose a valid date and meal type.'); return;
        }
        setBusy(true);
        try {
            let recipeId = privateId;
            if (!recipeId) {
                const saved = await saveSuggestedRecipe(recipe.id, mealType);
                recipeId = saved.id; setPrivateId(recipeId);
                window.dispatchEvent(new Event('panned-suggestion-saved'));
            }
            await addMeal({recipeId,date,mealType});
            navigate(`/calendar?${new URLSearchParams({date})}`);
        } catch(error) { setError(error.message); }
        finally { setBusy(false); }
    }
    return <form className="schedule-recipe" onSubmit={submit} aria-label={`Schedule ${recipe.name}`}>
        <h2>Add to Calendar</h2>
        {recipe.source === 'suggested' && <p>This recipe will be saved to My Recipes before scheduling.</p>}
        <fieldset disabled={busy}>
            <label>Date<input type="date" required value={date} onChange={event=>setDate(event.target.value)} autoFocus /></label>
            <label>Meal type<select aria-label="Meal type" required value={mealType} onChange={event=>setMealType(event.target.value)}>
                <option value="">Choose a meal type</option>
                {['Breakfast','Lunch','Dinner','Snack'].map(type=><option key={type}>{type}</option>)}
            </select></label>
            <button type="submit">{busy ? 'Scheduling…' : 'Schedule meal'}</button>
            <button type="button" onClick={onCancel}>Cancel</button>
        </fieldset>
        {error && <p role="alert">{error} You can retry scheduling.</p>}
    </form>;
}
