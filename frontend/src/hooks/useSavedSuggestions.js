import { useEffect, useState } from 'react';
import { getRecipes } from '../api/recipes';
import { useAuth } from '../auth/AuthContext';

export function useSavedSuggestions() {
    const { user } = useAuth();
    const [revision, setRevision] = useState(0);
    const [result, setResult] = useState(null);
    const key = `${user?.id}:${revision}`;
    useEffect(() => {
        if (!user) return;
        let active = true;
        getRecipes({ filter: 'saved' }).then(recipes => {
            if (active) setResult({ key, ids: Object.fromEntries(recipes.filter(r => r.suggestedId).map(r => [r.suggestedId, r.id])) });
        }).catch(error => { if (active) setResult({ key, ids: {}, error: error.message }); });
        const changed = () => setRevision(value => value + 1);
        window.addEventListener('panned-suggestion-saved', changed);
        return () => { active = false; window.removeEventListener('panned-suggestion-saved', changed); };
    }, [key, user]);
    return { ids: result?.key === key ? result.ids : {}, loading: result?.key !== key,
        error: result?.key === key ? result.error : '', retry: () => setRevision(value => value + 1) };
}
