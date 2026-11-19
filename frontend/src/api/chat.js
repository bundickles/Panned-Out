export async function chatRequest(message, history = [], signal) {
    let response;
    try {
        response = await fetch('/api/chat', {
            method: message === undefined ? 'GET' : 'POST',
            credentials: 'same-origin', signal,
            headers: message === undefined ? {} : { 'X-Panned-Out-Request': '1' },
            body: message === undefined ? undefined : new URLSearchParams({ message, history: JSON.stringify(history) }),
        });
    } catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new Error('Cannot reach the chat server. Please try again.');
    }
    if (response.status === 401) window.dispatchEvent(new Event('panned-session-expired'));
    let result;
    try { result = await response.json(); }
    catch { throw new Error('The chat server is unavailable. Please try again.'); }
    if (!response.ok) throw new Error(result.error || 'Unable to send your message. Please try again.');
    if (message !== undefined && typeof result.reply !== 'string') throw new Error('The chat reply was unreadable. Please try again.');
    return result;
}
