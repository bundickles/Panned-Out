import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Sidebar from '../../components/Sidebar/Sidebar.jsx';
import { useAuth } from '../../auth/AuthContext';
import { getShoppingList, validateRange } from '../../api/shopping';
import './Shopping.css';

function dateKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function dateFromKey(value) {
    if (validateRange(value || '', value || '')) return null;
    const [year, month, day] = value.split('-').map(Number);
    const date = new Date(0);
    date.setFullYear(year, month - 1, day);
    date.setHours(0, 0, 0, 0);
    return date;
}

function weekRange(date) {
    const first = new Date(date);
    first.setDate(first.getDate() - first.getDay());
    const last = new Date(first);
    last.setDate(first.getDate() + 6);
    return { start: dateKey(first), end: dateKey(last) };
}

export default function Shopping() {
    const { user } = useAuth();
    const [params, setParams] = useSearchParams();
    // Keep Vanny's week links working alongside the API's explicit date range.
    const defaultRange = weekRange(dateFromKey(params.get('week')) || new Date());
    const start = params.get('start') ?? defaultRange.start;
    const end = params.get('end') ?? defaultRange.end;
    const [revision, setRevision] = useState(0);
    const [result, setResult] = useState(null);
    const [collapsed, setCollapsed] = useState(false);
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

    // Never render results from another range, account, or refresh attempt.
    const current = result?.key === requestKey ? result : null;
    const data = current?.data;
    const busy = !validation && !current;
    const firstDate = dateFromKey(start);
    const lastDate = dateFromKey(end);
    const rangeLabel = firstDate && lastDate
        ? `${firstDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${lastDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
        : 'Choose your dates';

    function changeRange(key, value) {
        setParams({ start, end, [key]: value });
    }

    function changeWeek(days) {
        if (validation) return;
        firstDate.setDate(firstDate.getDate() + days);
        lastDate.setDate(lastDate.getDate() + days);
        setParams({ start: dateKey(firstDate), end: dateKey(lastDate) });
    }

    return <main className="shopping-page">
        <Sidebar />
        <div className="shopping-content">
            <div className="shopping-main">
                <header className="shopping-heading">
                    <div>
                        <p className="shopping-eyebrow">PANNED OUT / SHOPPING LIST</p>
                        <h1>Weekly Groceries</h1>
                        <p>Everything you need for the meals you're planning.</p>
                    </div>
                    <button className="shopping-primary" disabled={busy || !!validation} onClick={() => setRevision(value => value + 1)}>Generate from Meal Plan</button>
                </header>
                <div className="shopping-week-picker">
                    <button disabled={!!validation} onClick={() => changeWeek(-7)} aria-label="Previous week">←</button>
                    <div><span>SHOPPING DATES</span><strong>{rangeLabel}</strong></div>
                    <button disabled={!!validation} onClick={() => changeWeek(7)} aria-label="Next week">→</button>
                    <button className="shopping-this-week" onClick={() => setParams(weekRange(new Date()))}>This week</button>
                </div>
                <div className="shopping-date-range">
                    <label>Start date<input type="date" value={start} onChange={event => changeRange('start', event.target.value)} /></label>
                    <label>End date<input type="date" value={end} onChange={event => changeRange('end', event.target.value)} /></label>
                </div>
                {validation && <p className="shopping-notice" role="alert">{validation}</p>}
                {busy && <p className="shopping-notice" role="status">Loading shopping list...</p>}
                {current?.error && <div className="shopping-notice" role="alert">
                    <p>{current.error}</p>
                    <button className="shopping-outline" onClick={() => setRevision(value => value + 1)}>Retry</button>
                </div>}
                {data && <div aria-live="polite">
                    {data.warnings.length > 0 && <section className="shopping-notice" aria-label="Missing recipes">
                        <h2>Some ingredients are unavailable</h2>
                        <ul>{data.warnings.map((warning, index) => <li key={index}>{warning.source.recipeName} ({warning.source.date}): {warning.message}</li>)}</ul>
                    </section>}
                    <div className="shopping-list-actions"><h2>Your Ingredients</h2></div>
                    {data.items.length === 0 ? <p className="shopping-empty">No ingredients found for these dates. Schedule meals in the Calendar to build your list.</p>
                        : <section className="shopping-aisle">
                            <button className="shopping-aisle-header" onClick={() => setCollapsed(value => !value)} aria-expanded={!collapsed} aria-controls="generated-ingredients">
                                <span className="shopping-aisle-icon" aria-hidden="true">▤</span>
                                <strong>Ingredients</strong>
                                <span className="shopping-aisle-count">{data.items.length} {data.items.length === 1 ? 'item' : 'items'}</span>
                                <span className="shopping-chevron" aria-hidden="true">{collapsed ? '⌄' : '⌃'}</span>
                            </button>
                            <div id="generated-ingredients" className="shopping-aisle-body" hidden={collapsed}>
                                <ul className="shopping-generated-items">{data.items.map(item => <li key={item.name} className="shopping-item">
                                    <div className="shopping-generated-item">
                                        <strong>{item.name}</strong>
                                        <p className="shopping-quantity">{item.occurrences} {item.occurrences === 1 ? 'occurrence' : 'occurrences'}</p>
                                        <ul className="shopping-sources">{item.sources.map((source, index) => <li key={`${source.mealId}-${index}`}>{source.recipeName} — {source.date}</li>)}</ul>
                                    </div>
                                </li>)}</ul>
                            </div>
                        </section>}
                </div>}
            </div>
            <aside className="shopping-sidepanel">
                <section className="shopping-panel-card">
                    <h2>Your meal plan</h2>
                    <p>This list uses the recipes saved for your scheduled meals. Change your meals in the Calendar, then generate again to refresh the ingredients.</p>
                    <Link className="shopping-text-link" to="/calendar">View Calendar →</Link>
                </section>
                <section className="shopping-panel-card">
                    <h2>Reading your list</h2>
                    <p>Each ingredient line is shown as entered in your recipes. Occurrences count repeated lines across scheduled meals; quantities are not combined.</p>
                    <Link className="shopping-text-link" to="/recipes">View Recipes →</Link>
                </section>
                <div className="shopping-quote">Good food<br />brings people<br />together. ♡</div>
            </aside>
        </div>
    </main>;
}
