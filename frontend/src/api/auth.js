export async function authRequest(action, fields) {
    let response;
    try {
        response = await fetch(`/api/auth/${action}`, {
            method: fields === undefined ? 'GET' : 'POST',
            credentials: 'same-origin',
            headers: fields === undefined ? {} : { 'X-Panned-Out-Request': '1' },
            body: fields === undefined ? undefined : new URLSearchParams(fields),
        });
    } catch {
        throw new Error('Cannot reach the server. Please try again.');
    }
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The server is unavailable. Please try again.'); }
    if (action === 'me' && response.status === 401) return null;
    if (!response.ok) throw new Error(data.error || 'Unable to sign in. Please try again.');
    return data;
}
