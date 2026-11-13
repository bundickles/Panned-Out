async function request(path = '', options = {}) {
    let response;
    try {
        response = await fetch(`/api/recipes${path}`, { ...options, credentials: "same-origin", headers: { ...options.headers, "X-Panned-Out-Request": "1" } });
    } catch {
        throw new Error('Cannot reach the recipe server. Check that it is running and try again.');
    }
    let data;
    try {
        data = await response.json();
    } catch {
        throw new Error('The recipe server is unavailable. Please try again.');
    }
    if (response.status === 401) window.dispatchEvent(new Event("panned-session-expired"));
    if (!response.ok) {
        const error = new Error(data.error || 'Unable to load recipes. Please try again.');
        error.status = response.status;
        throw error;
    }
    return data;
}

export const getRecipes = ({ filter, signal } = {}) => request(filter ? `?${new URLSearchParams({ filter })}` : '', { signal });
export const createRecipe = (fields) => request('', { method: 'POST', body: new URLSearchParams(fields) });
export const removeRecipe = (id) => request(`/${encodeURIComponent(id)}`, { method: 'DELETE' });

export const updateRecipe = (id, fields) => request(`/${encodeURIComponent(id)}`, { method: 'PUT', body: new URLSearchParams(fields) });

export const saveSuggestedRecipe = (id, mealType) => request(`/${encodeURIComponent(id)}/save`, { method: 'POST', body: new URLSearchParams({ mealType }) });
