import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Sidebar from '../../components/Sidebar/Sidebar.jsx';
import { useAuth } from '../../auth/AuthContext';
import { getShoppingList, validateRange } from '../../api/shopping';
import './Shopping.css';

function dateKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export default function Shopping() {
    const { user } = useAuth();
    const [params, setParams] = useSearchParams();
    const today = new Date();
    const week = new Date(today.getFullYear(), today.getMonth(), today.getDate() - today.getDay());
    const last = new Date(week); last.setDate(last.getDate() + 6);
    const start = params.get('start') ?? dateKey(week);
    const end = params.get('end') ?? dateKey(last);
    const [revision, setRevision] = useState(0);
    const [result, setResult] = useState(null);
    const validation = validateRange(start, end);
    const requestKey = JSON.stringify([user.id, start, end, revision]);

    useEffect(() => {
        if (validation) return;
        const controller = new AbortController();
        let active = true;
        getShoppingList(start, end, { signal: controller.signal }).then(data => {
            if (active) setResult({ key: requestKey, data });
        }).catch(error => {
            if (active && error.name !== 'AbortError') setResult({ key: requestKey, error: error.message });
        });
        return () => { active = false; controller.abort(); };
    }, [start, end, requestKey, validation]);

    // Never render results from a different range, account, or refresh attempt.
    const current = result?.key === requestKey ? result : null;
    const data = current?.data;
    const busy = !validation && !current;
    function changeRange(key, value) { setParams({ start, end, [key]: value }); }

    return <main className="shopping-page">
        <Sidebar />
        <div className="shopping-content">
            <div className="shopping-main">
                <header className="shopping-heading">
                    <div><p className="shopping-eyebrow">PANNED OUT / SHOPPING LIST</p>
                        <h1>Weekly Groceries</h1><p>Ingredients for your scheduled meals.</p></div>
                    <button className="shopping-primary" disabled={busy || !!validation} onClick={() => setRevision(value => value + 1)}>Generate from Meal Plan</button>
                </header>
                <div className="shopping-week-picker">
                    <label>Start date<input type="date" value={start} onChange={event => changeRange('start', event.target.value)} /></label>
                    <label>End date<input type="date" value={end} onChange={event => changeRange('end', event.target.value)} /></label>
                </div>
                {validation && <p role="alert">{validation}</p>}
                {busy && <p role="status">Loading shopping list...</p>}
                {current?.error && <div role="alert"><p>{current.error}</p><button className="shopping-outline" onClick={() => setRevision(value => value + 1)}>Retry</button></div>}
                {data && <div aria-live="polite">
                    {data.warnings.length > 0 && <section className="shopping-notice" aria-label="Missing recipes">
                        <h2>Some ingredients are unavailable</h2>
                        <ul>{data.warnings.map((warning, index) => <li key={index}>{warning.source.recipeName} ({warning.source.date}): {warning.message}</li>)}</ul>
                    </section>}
                    {data.items.length === 0 ? <p className="shopping-empty">No ingredients found for these dates. Schedule meals in the Calendar to build your list.</p>
                        : <section className="shopping-aisle"><h2>Ingredients</h2><ul>{data.items.map(item => <li key={item.name} className="shopping-item">
                            <div><strong>{item.name}</strong><p>{item.occurrences} {item.occurrences === 1 ? 'occurrence' : 'occurrences'}</p>
                                <ul>{item.sources.map((source, index) => <li key={`${source.mealId}-${index}`}>{source.recipeName} — {source.date}</li>)}</ul>
                            </div>
                        </li>)}</ul></section>}
                </div>}
            </div>
            <aside className="shopping-sidepanel"><section className="shopping-panel-card"><h2>Your meal plan</h2>
                <p>Each ingredient line is shown as entered in your recipes. Occurrences count repeated lines across scheduled meals; quantities are not combined.</p>
                <Link to="/calendar">View Calendar →</Link>
            </section></aside>
        </div>
    </main>;
}
