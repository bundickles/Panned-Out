export function validateRange(start, end) {
    const valid = value => /^\d{4}-\d{2}-\d{2}$/.test(value) && !value.startsWith('0000')
        && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
    if (!valid(start) || !valid(end)) return 'Choose valid start and end dates.';
    return start > end ? 'Start date must be on or before end date.' : '';
}

export async function getShoppingList(start, end, { signal } = {}) {
    const validation = validateRange(start, end);
    if (validation) throw new Error(validation);
    let response;
    try {
        response = await fetch(`/api/shopping-list?${new URLSearchParams({ start, end })}`, {
            credentials: 'same-origin', signal, headers: { 'X-Panned-Out-Request': '1' },
        });
    } catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new Error('Cannot reach the shopping list server. Please try again.');
    }
    if (response.status === 401) window.dispatchEvent(new Event('panned-session-expired'));
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The shopping list server is unavailable. Please try again.'); }
    if (!response.ok) throw new Error(data.error || 'Unable to load shopping list. Please try again.');
    return data;
}
