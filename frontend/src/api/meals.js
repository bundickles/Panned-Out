async function request(path = '', options = {}) {
    let response;
    try {
        response = await fetch(`/api/meals${path}`, {
            ...options, credentials: 'same-origin',
            headers: { 'X-Panned-Out-Request': '1' },
        });
    } catch {
        throw new Error('Cannot reach the server. Please try again.');
    }
    if (response.status === 401) window.dispatchEvent(new Event('panned-session-expired'));
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The meal service is unavailable. Please try again.'); }
    if (!response.ok) throw new Error(data.error || 'Unable to update meals. Please try again.');
    return data;
}

export const getMeals = () => request();
export const addMeal = (fields) => request('', { method: 'POST', body: new URLSearchParams(fields) });
export const removeMeal = (id) => request(`/${encodeURIComponent(id)}`, { method: 'DELETE' });
