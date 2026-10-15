import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import "./Shopping.css";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";

const AISLES = [
  { name: "Produce", symbol: "✿" },
  { name: "Deli", symbol: "◈" },
  { name: "Meat & Seafood", symbol: "♧" },
  { name: "Dairy & Eggs", symbol: "◌" },
  { name: "Pantry & Grains", symbol: "▤" },
  { name: "Frozen", symbol: "❄" },
  { name: "Bakery", symbol: "❧" },
  { name: "Other", symbol: "＋" },
];

function startOfWeek(date) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  copy.setDate(copy.getDate() - copy.getDay()); // Sunday–Saturday, same as Calendar.jsx
  return copy;
}
function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function dateFromKey(key) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(key || "")) return null;
  const [year, month, day] = key.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return dateKey(date) === key ? date : null;
}
function safeItems(key) {
  try {
    const value = JSON.parse(localStorage.getItem(`panned-out-shopping-${key}`));
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}
function uid() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function Shopping() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const queryWeek = dateFromKey(params.get("week"));
  const week = startOfWeek(queryWeek || new Date());
  const weekKey = dateKey(week);
  const lastDay = new Date(week);
  lastDay.setDate(week.getDate() + 6);
  const listStorageKey = `panned-out-shopping-${weekKey}`;
  const budgetStorageKey = `panned-out-budget-${weekKey}`;

  const [items, setItems] = useState(() => safeItems(weekKey));
  const [budget, setBudget] = useState(() => localStorage.getItem(budgetStorageKey) || "");
  const [loadedWeek, setLoadedWeek] = useState(weekKey);
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [aisle, setAisle] = useState("Produce");
  const [showAdd, setShowAdd] = useState(false);
  const [collapsed, setCollapsed] = useState([]);
  const [notice, setNotice] = useState("");

  // Load only the currently selected week's list; do not overwrite other weeks.
  useEffect(() => {
    setItems(safeItems(weekKey));
    setBudget(localStorage.getItem(budgetStorageKey) || "");
    setCollapsed([]);
    setNotice("");
    setLoadedWeek(weekKey);
  }, [weekKey, budgetStorageKey]);
  useEffect(() => {
    if (loadedWeek === weekKey) localStorage.setItem(listStorageKey, JSON.stringify(items));
  }, [items, listStorageKey, loadedWeek, weekKey]);
  useEffect(() => {
    if (loadedWeek === weekKey) localStorage.setItem(budgetStorageKey, budget);
  }, [budget, budgetStorageKey, loadedWeek, weekKey]);

  const completed = items.filter((item) => item.checked).length;
  const progress = items.length ? (completed / items.length) * 100 : 0;
  const grouped = useMemo(() => AISLES.map((entry) => ({
    ...entry,
    items: items.filter((item) => item.aisle === entry.name),
  })), [items]);

  function changeWeek(days) {
    const next = new Date(week);
    next.setDate(next.getDate() + days);
    setParams({ week: dateKey(next) });
  }
  function addItem(event) {
    event.preventDefault();
    if (!name.trim()) return;
    setItems((current) => [...current, {
      id: uid(), name: name.trim(), quantity: quantity.trim(), aisle, checked: false,
    }]);
    setName("");
    setQuantity("");
    setShowAdd(false);
    setNotice("");
  }
  function toggleItem(id) {
    setItems((current) => current.map((item) => item.id === id ? { ...item, checked: !item.checked } : item));
  }
  function deleteItem(id) {
    setItems((current) => current.filter((item) => item.id !== id));
  }
  function clearCompleted() {
    if (!completed) return;
    setItems((current) => current.filter((item) => !item.checked));
  }
  function deleteAll() {
    if (items.length && window.confirm("Delete every item from this week's shopping list?")) setItems([]);
  }
  function toggleAisle(name) {
    setCollapsed((current) => current.includes(name) ? current.filter((item) => item !== name) : [...current, name]);
  }
  function generateList() {
    setNotice("Weekly recipe generation isn't connected yet. Once planned meals are saved in the backend, this button will collect their ingredients for the selected week.");
  }
  const weekLabel = `${week.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${lastDay.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;

  return (
    <main className="shopping-page">
      <Sidebar />
      {/* <div>Sidebar test</div> */}

      <div className="shopping-content">
        <div className="shopping-main">
          <header className="shopping-heading">
            <div>
              <p className="shopping-eyebrow">PANNED OUT / SHOPPING LIST</p>
              <h1>Weekly Groceries</h1>
              <p>Everything you need for the meals you're planning.</p>
            </div>
            <button className="shopping-primary" onClick={generateList}>↻ &nbsp; Generate from Meal Plan</button>
          </header>
          <div className="shopping-week-picker">
            <button onClick={() => changeWeek(-7)} aria-label="Previous week">←</button>
            <div><span>SHOPPING WEEK</span><strong>{weekLabel}</strong></div>
            <button onClick={() => changeWeek(7)} aria-label="Next week">→</button>
            <button className="shopping-this-week" onClick={() => setParams({ week: dateKey(startOfWeek(new Date())) })}>This week</button>
          </div>
          {notice && <p className="shopping-notice" role="status">{notice}</p>}
          <div className="shopping-progress">
            <div className="shopping-progress-top"><strong>{completed} of {items.length} items checked</strong><span>{items.length ? `${Math.round(progress)}% done` : "Your list is empty"}</span></div>
            <div className="shopping-progress-track"><div style={{ width: `${progress}%` }} /></div>
          </div>

          <div className="shopping-list-actions">
            <h2>Shop by Aisle</h2>
            <button className="shopping-primary" onClick={() => setShowAdd((value) => !value)}>+ Add Item</button>
          </div>
          {showAdd && (
            <form className="shopping-add-form" onSubmit={addItem}>
              <label>Item name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Bell peppers" required autoFocus /></label>
              <label>Quantity<input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="e.g. 3, 1 lb" /></label>
              <label>Aisle<select value={aisle} onChange={(e) => setAisle(e.target.value)}>{AISLES.map((entry) => <option key={entry.name}>{entry.name}</option>)}</select></label>
              <div className="shopping-form-buttons"><button type="submit" className="shopping-primary">Add to list</button><button type="button" className="shopping-outline" onClick={() => setShowAdd(false)}>Cancel</button></div>
            </form>
          )}
          {items.length === 0 && <p className="shopping-empty">Your shopping list is ready to fill. Add your first item, or generate ingredients from your meal plan when that feature is connected.</p>}
          <div className="shopping-aisles">
            {grouped.map((group) => (
              <section key={group.name} className="shopping-aisle">
                <button className="shopping-aisle-header" onClick={() => toggleAisle(group.name)} aria-expanded={!collapsed.includes(group.name)}>
                  <span className="shopping-aisle-icon" aria-hidden="true">{group.symbol}</span>
                  <strong>{group.name}</strong>
                  <span className="shopping-aisle-count">{group.items.length} {group.items.length === 1 ? "item" : "items"}</span>
                  <span className="shopping-chevron" aria-hidden="true">{collapsed.includes(group.name) ? "⌄" : "⌃"}</span>
                </button>
                {!collapsed.includes(group.name) && (
                  <div className="shopping-aisle-body">
                    {group.items.length ? group.items.map((item) => (
                      <div key={item.id} className={`shopping-item ${item.checked ? "checked" : ""}`}>
                        <label className="shopping-item-check"><input type="checkbox" checked={item.checked} onChange={() => toggleItem(item.id)} /><span>{item.name}</span></label>
                        <span className="shopping-quantity">{item.quantity}</span>
                        <button className="shopping-delete" aria-label={`Delete ${item.name}`} title="Delete item" onClick={() => deleteItem(item.id)}>✕</button>
                      </div>
                    )) : <p className="shopping-aisle-empty">No items in this aisle yet.</p>}
                    <button className="shopping-inline-add" onClick={() => { setAisle(group.name); setShowAdd(true); }}>+ Add to {group.name}</button>
                  </div>
                )}
              </section>
            ))}
          </div>
        </div>

        <aside className="shopping-sidepanel">
          <section className="shopping-panel-card">
            <h2>Quick Actions</h2>
            <button className="shopping-primary" onClick={generateList}>↻ Generate from Meal Plan</button>
            <button className="shopping-outline" disabled={!completed} onClick={clearCompleted}>Clear Completed Items</button>
            <button className="shopping-outline" disabled={!items.length} onClick={deleteAll}>Delete All Items</button>
          </section>
          <section className="shopping-panel-card">
            <h2>Estimated Budget</h2>
            <span className="shopping-budget-label">Estimated Total</span>
            <div className="shopping-budget-total">Not available yet</div>
            <label className="shopping-budget-goal">Your budget goal ($)<input min="0" step="0.01" type="number" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="e.g. 100.00" /></label>
            <p>Once ingredient prices are available, your weekly estimate and remaining budget will appear here.</p>
          </section>
          <section className="shopping-panel-card">
            <h2>This Week's Meals</h2>
            <p>Meal details will appear here once the calendar's weekly meal data is connected.</p>
            <button className="shopping-text-link" onClick={() => navigate("/calendar")}>View Calendar →</button>
          </section>
          <div className="shopping-quote">Good food<br />brings people<br />together. ♡</div>
        </aside>
      </div>
    </main>
  );
}
