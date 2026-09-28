import { useState } from "react";
import { useNavigate } from "react-router-dom";

import "./Calendar.css";    
import MealCard from "../../components/MealCard/MealCard";

function Calendar() {
    const navigate = useNavigate();
    const today = new Date();

    const [currentDate, setCurrentDate] = useState(
        new Date(today.getFullYear(), today.getMonth(), 1)
    );

    const [selectedDate, setSelectedDate] = useState(
        new Date(today.getFullYear(), today.getMonth(), today.getDate())
    );

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

    // Temporary meal data

    const meals = {
        // Example:
        // "2026-09-27" : [...]
    };

    const selectedDateKey = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;

    const selectedMeals = meals[selectedDateKey] || [];

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
                                    
                                    onClick={() => selectDay(day)}
                                >
                                    <span className="calendar-date">
                                        {day.getDate()}
                                    </span>

                                    {/*Future meal indicators can be added here*/}
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

                        <button className="add-meal-button">
                            + Add Meal
                        </button>
                    </div>

                    {selectedMeals.length > 0 ? (

                        <div className="meals-list">

                            {selectedMeals.map((meal) => (
                                <MealCard
                                    key={meal.id}
                                    meal={meal}
                                />

                            ))}
                        </div>
                    ) : (

                        <div className="empty-meals">
                            <h3>No meals for this day.</h3>

                            <p>Add a meal to start planning your day.</p>

                            <button className="add-meal-button">
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