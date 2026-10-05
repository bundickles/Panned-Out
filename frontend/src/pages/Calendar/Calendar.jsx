import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import "./Calendar.css";    
import MealCard from "../../components/MealCard/MealCard";

import AddMealForm from "./AddMealForm";
import { getMeals, addMeal, removeMeal } from "../../api/meals";

const dateKey = day => `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;

function Calendar() {
    const navigate = useNavigate();
    const today = new Date();

    const [currentDate, setCurrentDate] = useState(
        new Date(today.getFullYear(), today.getMonth(), 1)
    );

    const [selectedDate, setSelectedDate] = useState(
        new Date(today.getFullYear(), today.getMonth(), today.getDate())
    );

    const [meals, setMeals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const [actionError, setActionError] = useState('');
    const [showForm, setShowForm] = useState(false);
    const [removing, setRemoving] = useState(null);
    const [revision, setRevision] = useState(0);

    useEffect(() => {
        let active = true;
        getMeals().then(data => { if (active) setMeals(data); })
            .catch(error => { if (active) setLoadError(error.message); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [revision]);

    async function saveMeal(fields) {
        const saved = await addMeal(fields);
        setMeals(current => [...current, saved]);
        setShowForm(false);
        setActionError('');
    }

    async function deleteMeal(id) {
        setRemoving(id);
        setActionError('');
        try {
            await removeMeal(id);
            setMeals(current => current.filter(meal => meal.id !== id));
        } catch (error) { setActionError(error.message); }
        finally { setRemoving(null); }
    }

    // Calendar calculations
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDayOfMonth = new Date(year, month, 1);
    const lastDayOfMonth = new Date(year, month + 1, 0);

    const daysInMonth = lastDayOfMonth.getDate();

    //Sunday = 0, Monday = 1, ..., Saturday = 6
    const startingDay = firstDayOfMonth.getDay();

    const monthName = currentDate.toLocaleString("default", { month: "long" });
    
    // Build calendar days
    const calendarDays = [];

    // Add empty days for the previous month
    for (let i = 0; i < startingDay; i++) {
        calendarDays.push(null);
    }

    // Add days for the current month
    for (let day = 1; day <= daysInMonth; day++) {
        calendarDays.push(new Date(year, month, day));
    }

    // Navigation
    function goToPreviousMonth () {
        setCurrentDate(new Date(year, month - 1, 1));
    };

    function goToNextMonth () {
        setCurrentDate(new Date(year, month + 1, 1));
    };

    function goToToday() {
        setCurrentDate(new Date(today.getFullYear(), today.getMonth(), 1));
        setSelectedDate(new Date(today.getFullYear(), today.getMonth(), today.getDate()));
    };

    // Date selection

    function selectDay(day) {
        setSelectedDate(day);
    }

    function isSelected(day) {
        if (!day) return false;

        return (
            selectedDate.getFullYear() === day.getFullYear() &&
            selectedDate.getMonth() === day.getMonth() &&
            selectedDate.getDate() === day.getDate()
        );
    }   

    function isToday(day) {
        if (!day) return false;

        return (
            today.getFullYear() === day.getFullYear() &&
            today.getMonth() === day.getMonth() &&
            today.getDate() === day.getDate()
        );
    }

    const selectedDateKey = dateKey(selectedDate);
    const selectedMeals = meals.filter(meal => meal.date === selectedDateKey);

    const selectedDateText = selectedDate.toLocaleDateString(
        "default", { weekday: "long", year: "numeric", month: "long", day: "numeric" }
    );

    return (
        <main className="calendar-page">
            {/*Sidebar*/}

            <aside className="calendar-sidebar">

                <div className="sidebar-logo">
                    Panned Out
                </div>

                <nav className="sidebar-nav">
                    <button 
                        className="nav-item"
                        onClick={() => navigate("/calendar")}>
                        <span>▦</span>
                        Calendar
                    </button>

                    <button 
                        className="nav-item"
                        onClick={() => navigate("/recipes")}>
                        <span>🍽</span>
                        Recipes
                    </button>
                </nav>

                <div className="sidebar-bottom">
                    <button className="nav-item">
                        <span>⚙️</span>
                        Settings
                    </button>
                </div>
            </aside>

            {/*Main Calendar*/}
            <section className="calendar-content">

                <header className="calendar-header">
                    <div>
                        <span className="calendar-eyebrow">
                            MEAL PLAN
                        </span>

                        <h1>
                            {monthName} {year}
                        </h1>
                    </div>

                    <div className="calendar-actions">
                        <button
                            className="today-button"
                            onClick={goToToday}
                        >
                        Today
                        </button>

                        <button
                            className="calendar-arrow"
                            onClick={goToPreviousMonth}
                            aria-label="Previous Month"
                        >
                         ◀
                        </button>

                        <button
                            className="calendar-arrow"
                            onClick={goToNextMonth}
                            aria-label="Next Month"
                        >
                         ▶
                        </button>
                    </div>
                </header>

                {/*Future view controls*/}
                <div className="calendar-view-controls">

                    <button className="view-button active">
                        Month
                    </button>
                    <button className="view-button">
                        Week
                    </button>
                    <button className="view-button">
                        Day
                    </button>
                </div>

                {/*Actual Calendar*/}

                <div className="calendar">
                    {/*Weekdays Header*/}
                    <div className="calendar-weekdays">
                        <span>Sun</span>
                        <span>Mon</span>
                        <span>Tue</span>
                        <span>Wed</span>
                        <span>Thu</span>
                        <span>Fri</span>
                        <span>Sat</span>
                    </div>

                    {/*Calendar Days*/}
                    <div className="calendar-grid">

                        {calendarDays.map((day, index) => {

                            if(!day){
                                return(
                                    <div
                                        key={`empty-${index}`}
                                        className="calendar-cell empty"
                                    ></div>
                                );
                            }

                            return(
                                <button
                                    key={day.toISOString()}
                                    className={`
                                        calendar-cell
                                        ${isSelected(day) ? "selected" : ""}
                                        ${isToday(day) ? "today" : ""}`}
                                    
                                    aria-label={dateKey(day)}
                                    aria-pressed={isSelected(day)}
                                    onClick={() => selectDay(day)}
                                >
                                    <span className="calendar-date">
                                        {day.getDate()}
                                    </span>

                                    {meals.some(meal => meal.date === dateKey(day)) && (
                                        <span className="meal-count">{meals.filter(meal => meal.date === dateKey(day)).length} planned</span>
                                    )}
                                    {isToday(day) && (
                                        <span className="today-label">Today</span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Selected Day's Meals */}
                <section className="meals-selection">
                    <div className="meals-heading">
                        <div>
                            <span>
                                {selectedDateText.toUpperCase()}
                            </span>
                            <h2>Meals</h2>
                        </div>

                        <button className="add-meal-button" disabled={loading || !!loadError} onClick={() => setShowForm(true)}>
                            + Add Meal
                        </button>
                    </div>

                    {showForm && <AddMealForm key={selectedDateKey} date={selectedDateKey} onSave={saveMeal} onCancel={() => setShowForm(false)} />}
                    {actionError && <p role="alert">{actionError}</p>}
                    {loading ? <p role="status">Loading meals...</p> : loadError ? (
                        <div role="alert">{loadError} <button onClick={() => {
                            setLoading(true); setLoadError(''); setRevision(value => value + 1);
                        }}>Retry meals</button></div>
                    ) : selectedMeals.length > 0 ? (

                        <div className="meals-list">

                            {selectedMeals.map((meal) => (
                                <div key={meal.id}>
                                    <MealCard meal={meal} />
                                    <button type="button" className="remove-meal-button" disabled={removing !== null} onClick={() => deleteMeal(meal.id)} aria-label={`Remove ${meal.name} from calendar`}>
                                        {removing === meal.id ? 'Removing...' : 'Remove meal'}
                                    </button>
                                </div>

                            ))}
                        </div>
                    ) : (

                        <div className="empty-meals">
                            <h3>No meals for this day.</h3>

                            <p>Add a meal to start planning your day.</p>

                            <button className="add-meal-button" disabled={loading || !!loadError} onClick={() => setShowForm(true)}>
                                + Add Meal
                            </button>
                        </div>
                    )}
                </section>
            </section>   
        </main>
    );
}
export default Calendar;