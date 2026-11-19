import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getRecipes } from '../../api/recipes';
import { addMealPlan } from '../../api/meals';

export default function SchedulePlan({ plan }) {
    const [recipes, setRecipes] = useState([]);
    const [selected, setSelected] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [start, setStart] = useState('');
    const [type, setType] = useState('Dinner');
    const [error, setError] = useState('');
    const [saved, setSaved] = useState(null);
    const [revision, setRevision] = useState(0);
    useEffect(() => {
        let active = true;
        getRecipes().then(data => {
            const eligible = data.filter(recipe => Number.isInteger(recipe.id)
                && (plan === 'Balanced' || recipe.category === plan));
            if (active) {
                setRecipes(eligible);
                setSelected(eligible.slice(0, 7).map(recipe => recipe.id));
            }
        }).catch(err => { if (active) setError(err.message); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [plan, revision]);

    async function schedule(event) {
        event.preventDefault();
        if (busy || !selected.length || !start) return;
        setBusy(true);
        setError('');
        try {
            const meals = await addMealPlan({ plan, startDate: start, mealType: type, recipeIds: selected.join(',') });
            setSaved({ meals, start });
        } catch (err) { setError(err.message); }
        finally { setBusy(false); }
    }
    if (saved) return <section className="plan-schedule" aria-label="Scheduled meal plan">
        <p role="status">Added {saved.meals.length} meals starting {saved.start}. Existing meals were kept.</p>
        <Link to={`/calendar?date=${encodeURIComponent(saved.start)}`}>View plan on calendar</Link>
    </section>;
    return <section className="plan-schedule" aria-label="Schedule meal plan">
        <h3>Add to Calendar</h3>
        <p>Choose your saved {plan === 'Balanced' ? '' : `${plan} `}recipes. Each selected recipe is scheduled on the next day, in the order listed. Existing meals stay in place.</p>
        {loading && <p role="status">Loading saved recipes…</p>}
        {error && <div role="alert">{error} <button type="button" disabled={busy} onClick={() => {
            setError(''); setLoading(true); setRevision(value => value + 1);
        }}>Reload recipes</button></div>}
        {!loading && !error && recipes.length === 0 && <p>Save a recipe{plan === 'Balanced' ? '' : ` in the ${plan} category`} on the Recipes page first. <Link to="/recipes">Open Recipes</Link></p>}
        {recipes.length > 0 && <form onSubmit={schedule}>
            <fieldset disabled={busy || loading}>
                <legend>Recipes to schedule (up to 31)</legend>
                {recipes.map(recipe => <label className="plan-recipe-option" key={recipe.id}>
                    <input type="checkbox" checked={selected.includes(recipe.id)}
                        disabled={!selected.includes(recipe.id) && selected.length >= 31}
                        onChange={event => setSelected(current => event.target.checked
                            ? recipes.filter(r => current.includes(r.id) || r.id === recipe.id).map(r => r.id)
                            : current.filter(id => id !== recipe.id))} />
                    {recipe.name}
                </label>)}
                <label htmlFor="plan-start-date">Start date</label>
                <input id="plan-start-date" type="date" min="0001-01-01" max="9999-12-01" required value={start} onChange={event => setStart(event.target.value)} />
                <label htmlFor="plan-meal-type">Meal type</label>
                <select id="plan-meal-type" value={type} onChange={event => setType(event.target.value)}>
                    {['Breakfast', 'Lunch', 'Dinner', 'Snack'].map(item => <option key={item}>{item}</option>)}
                </select>
                <p>{selected.length} meals selected</p>
                <button type="submit" className="modal-submit" disabled={!selected.length || !start || busy || loading}>
                    {busy ? 'Adding meals…' : 'Add to Calendar'}
                </button>
            </fieldset>
        </form>}
    </section>;
}
