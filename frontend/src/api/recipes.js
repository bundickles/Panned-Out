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
    if (!response.ok) throw new Error(data.error || 'Unable to update recipes. Please try again.');
    return data;
}

export const getRecipes = () => request();
export const createRecipe = (fields) => request('', { method: 'POST', body: new URLSearchParams(fields) });
export const removeRecipe = (id) => request(`/${encodeURIComponent(id)}`, { method: 'DELETE' });
