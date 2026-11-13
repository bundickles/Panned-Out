import SaveSuggestedRecipe from '../SaveSuggestedRecipe/SaveSuggestedRecipe';
import { useSavedSuggestions } from '../../hooks/useSavedSuggestions';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getRecipes } from '../../api/recipes';
import './PlanRecipes.css';

export default function PlanRecipes({ plan, filter = 'suggested', returnTo = '/meal-plans' }) {
    const navigate = useNavigate();
    const saved = useSavedSuggestions();
    const [result, setResult] = useState({ key: null, recipes: [], error: '' });
    const [reload, setReload] = useState(0);
    const requestKey = `${filter}:${reload}`;
    const loading = result.key !== requestKey;
    useEffect(() => {
        const controller = new AbortController();
        let active = true;
        getRecipes({ filter, signal: controller.signal }).then(recipes => {
            if (!Array.isArray(recipes)) throw new Error('The recipe server returned an unexpected response.');
            if (active) setResult({ key: requestKey, recipes, error: '' });
        }).catch(error => {
            if (!active) return;
            if (error.status === 401) {
                navigate('/login', { replace: true });
                return;
            }
            setResult({ key: requestKey, recipes: [], error: error.message });
        });
        return () => { active = false; controller.abort(); };
    }, [filter, requestKey, navigate]);

    const recipes = (loading ? [] : result.recipes).filter(recipe => !plan || recipe.plan === plan);
    return <section className="plan-recipes" aria-label={plan ? `${plan} recipes` : 'Browse recipes'} aria-busy={loading}>
        {saved.error && <div role="alert">{saved.error} <button type="button" onClick={saved.retry}>Retry saved state</button></div>}
        {loading ? <p role="status">Loading recipes…</p> : result.error ? <div role="alert">
            <p>{result.error}</p>
            <button type="button" onClick={() => setReload(value => value + 1)}>Retry loading recipes</button>
        </div> : recipes.length === 0 ? <p role="status">
            {plan ? `No recipes are available for ${plan} yet.` : 'No recipes are available for this filter yet.'}
        </p> : <>
            <p role="status">{recipes.length} {recipes.length === 1 ? 'recipe' : 'recipes'}</p>
            <ul className="plan-recipes-grid">
                {recipes.map(recipe => <li key={`${recipe.source}:${recipe.id}`}>
                    <Link to={`/recipes/${encodeURIComponent(recipe.id)}`} state={{ from: returnTo }}>
                        <h3>{recipe.name}</h3>
                        <p>{recipe.plan || recipe.category}</p>
                        <p>{recipe.difficulty || 'Difficulty unavailable'} · {recipe.prepTime == null ? 'Prep time unavailable' : `${recipe.prepTime} min prep`}</p>
                        <span>Open recipe →</span>
                    </Link>
                    <SaveSuggestedRecipe recipe={recipe} savedId={saved.ids[recipe.id]} checking={saved.loading} />
                </li>)}
            </ul>
        </>}
    </section>;
}
