import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getShoppingList, validateRange } from '../frontend/src/api/shopping.js';

test('dates reject impossible, blank, zero-year and reversed ranges', () => {
    for (const [start, end] of [['', '2026-10-07'], ['2026-02-30', '2026-10-07'], ['0000-01-01', '2026-10-07'], ['2026-10-08', '2026-10-07']]) {
        assert.notEqual(validateRange(start, end), '');
    }
    assert.equal(validateRange('2028-02-29', '2028-02-29'), '');
});

test('requests carry cookies, date parameters and cancellation; errors and expiry propagate', async () => {
    const originalFetch = globalThis.fetch;
    const originalWindow = globalThis.window;
    try {
        const controller = new AbortController();
        globalThis.fetch = async (url, options) => {
            assert.equal(url, '/api/shopping-list?start=2026-10-01&end=2026-10-07');
            assert.equal(options.credentials, 'same-origin');
            assert.equal(options.signal, controller.signal);
            return { ok: true, status: 200, json: async () => ({ items: [], warnings: [] }) };
        };
        assert.deepEqual(await getShoppingList('2026-10-01', '2026-10-07', { signal: controller.signal }), { items: [], warnings: [] });
        let expired = false;
        globalThis.window = { dispatchEvent: event => { expired = event.type === 'panned-session-expired'; } };
        globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ error: 'Sign in' }) });
        await assert.rejects(getShoppingList('2026-10-01', '2026-10-07'), /Sign in/);
        assert.equal(expired, true);
        globalThis.fetch = async () => { throw new Error('offline'); };
        await assert.rejects(getShoppingList('2026-10-01', '2026-10-07'), /Cannot reach/);
        globalThis.fetch = async () => { throw new DOMException('Cancelled', 'AbortError'); };
        await assert.rejects(getShoppingList('2026-10-01', '2026-10-07'), { name: 'AbortError' });
    } finally {
        globalThis.fetch = originalFetch;
        globalThis.window = originalWindow;
    }
});
