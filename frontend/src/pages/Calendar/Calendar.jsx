import { useEffect, useState } from "react";

import "./Calendar.css"; 
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import MealCard from "../../components/MealCard/MealCard";
import DailyMacroSummary from "../../components/DailyMacroSummary/DailyMacroSummary";
import { getRecipes } from "../../api/recipes";

import AddMealForm from "./AddMealForm";
import { getMeals, addMeal, removeMeal } from "../../api/meals";

function getMealTypeClass(type) {
  const value = String(type || "").trim().toLowerCase();

  return ["breakfast", "lunch", "dinner", "snack"]
    .includes(value)
    ? value
    : "other";
}

function Calendar() {
    const today = new Date();
    const [view, setView] = useState("month");

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
    const [recipes, setRecipes] = useState([]);
    const [recipesError, setRecipesError] = useState("");

    useEffect(() => {
    let active = true;

    setLoading(true);
    setLoadError("");
    setRecipesError("");

    Promise.allSettled([getMeals(), getRecipes()])
        .then(([mealResult, recipeResult]) => {
        if (!active) return;

        if (mealResult.status === "fulfilled") {
            setMeals(mealResult.value);
        } else {
            setLoadError(
            mealResult.reason?.message || "Unable to load meals."
            );
        }

        if (recipeResult.status === "fulfilled") {
            setRecipes(recipeResult.value);
        } else {
            setRecipes([]);
            setRecipesError(
            recipeResult.reason?.message ||
            "Unable to load recipe nutrition."
            );
        }
        })
        .finally(() => {
        if (active) setLoading(false);
        });

    return () => {
        active = false;
    };
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

    
    const weekStart = new Date(selectedDate);
    weekStart.setHours(0, 0, 0, 0);
    weekStart.setDate(
        weekStart.getDate() - weekStart.getDay()
    );

    const weekDays = Array.from({ length: 7 }, (_, index) => {
        const day = new Date(weekStart);
        day.setDate(weekStart.getDate() + index);
        return day;
    });

    function getDateKey(date) {
        return `${date.getFullYear()}-${String(
            date.getMonth() + 1
        ).padStart(2, "0")}-${String(
            date.getDate()
        ).padStart(2, "0")}`;
    }

    // Navigation

    function goToPreviousMonth() {
        if (view === "month") {
            setCurrentDate(
                new Date(year, month - 1, 1)
            );
        } else {
            const nextSelectedDate = new Date(selectedDate);

            if (view === "week") {
                nextSelectedDate.setDate(
                    nextSelectedDate.getDate() - 7
                );
            } else {
                nextSelectedDate.setDate(
                    nextSelectedDate.getDate() - 1
                );
            }

            setSelectedDate(nextSelectedDate);
            setCurrentDate(
                new Date(
                    nextSelectedDate.getFullYear(),
                    nextSelectedDate.getMonth(),
                    1
                )
            );
        }
    }

    function goToNextMonth() {
        if (view === "month") {
            setCurrentDate(
                new Date(year, month + 1, 1)
            );
        } else {
            const nextSelectedDate = new Date(selectedDate);

            if (view === "week") {
                nextSelectedDate.setDate(
                    nextSelectedDate.getDate() + 7
                );
            } else {
                nextSelectedDate.setDate(
                    nextSelectedDate.getDate() + 1
                );
            }

            setSelectedDate(nextSelectedDate);
            setCurrentDate(
                new Date(
                    nextSelectedDate.getFullYear(),
                    nextSelectedDate.getMonth(),
                    1
                )
            );
        }
    }

    function goToToday() {
        const now = new Date();

        setCurrentDate(
            new Date(now.getFullYear(), now.getMonth(), 1)
        );

        setSelectedDate(
            new Date(now.getFullYear(), now.getMonth(), now.getDate())
        );
    }


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

    const selectedDateKey = getDateKey(selectedDate);
    const recipesById = new Map(
    recipes.map((recipe) => [String(recipe.id), recipe])
    );

    const selectedMeals = meals
    .filter((meal) => meal.date === selectedDateKey)
    .map((meal) => {
        const recipe = recipesById.get(String(meal.recipeId));

        if (!recipe) {
        return {
            ...meal,
            nutritionAvailable: false,
        };
        }

        const nutrientFields = [
        "calories",
        "protein",
        "carbohydrates",
        "fat",
        ];

        const nutritionAvailable = nutrientFields.every(
        (field) =>
            recipe[field] !== null &&
            recipe[field] !== undefined &&
            recipe[field] !== "" &&
            Number.isFinite(Number(recipe[field]))
        );

        return {
        ...meal,
        image: recipe.image || meal.image || "",
        calories: recipe.calories,
        protein: recipe.protein,
        carbohydrates: recipe.carbohydrates,
        fat: recipe.fat,
        nutritionAvailable,
        };
    });

    const selectedDateText = selectedDate.toLocaleDateString(
        "default", { weekday: "long", year: "numeric", month: "long", day: "numeric" }
    );

    return (
        <main className="calendar-page">
            {/*Sidebar*/}

           <Sidebar />
            {/* <div>Sidebar test</div> */}

            {/*Main Calendar*/}
            <section className="calendar-content" tabIndex={0} aria-label="Calendar content">

                <header className="calendar-header">
                    <div>
                        <span className="calendar-eyebrow">
                            MEAL PLAN
                        </span>

                        <h1>
                            {view === "month"
                                ? `${monthName} ${year}`
                                : view === "week"
                                    ? `Week of ${weekStart.toLocaleDateString("en-US", {
                                        month: "long",
                                        day: "numeric"
                                    })}`
                                    : selectedDate.toLocaleDateString("en-US", {
                                        month: "long",
                                        day: "numeric",
                                        year: "numeric"
                                    })}
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
                    <button
                        className={`view-button ${view === "month" ? "active" : ""}`}
                        onClick={() => setView("month")}
                        aria-pressed={view === "month"}
                    >
                        Month
                    </button>

                    <button
                        className={`view-button ${view === "week" ? "active" : ""}`}
                        onClick={() => setView("week")}
                        aria-pressed={view === "week"}
                    >
                        Week
                    </button>

                    <button
                        className={`view-button ${view === "day" ? "active" : ""}`}
                        onClick={() => setView("day")}
                        aria-pressed={view === "day"}
                    >
                        Day
                    </button>
                </div>


                {/*Actual Calendar*/}
                {view === "month" && (
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

                                const dayMeals = meals.filter(
                                (meal) => meal.date === getDateKey(day)
                                );

                                return(
                                    <button
                                        key={day.toISOString()}
                                        className={`
                                            calendar-cell
                                            ${isSelected(day) ? "selected" : ""}
                                            ${isToday(day) ? "today" : ""}`}
                                    
                                        aria-label={`${getDateKey(day)}: ${dayMeals.length} planned meals`}
                                    aria-pressed={isSelected(day)}
                                    onClick={() => selectDay(day)}
                                    >
                                        <span className="calendar-date">
                                            {day.getDate()}
                                        </span>

                                        {dayMeals.length > 0 && (
                                        <span className="calendar-meal-dots" aria-hidden="true">
                                            {dayMeals.slice(0, 4).map((meal, index) => (
                                            <span
                                                key={meal.id ?? index}
                                                className={`calendar-meal-dot meal-type-${getMealTypeClass(meal.type)}`}
                                            />
                                            ))}

                                            {dayMeals.length > 4 && (
                                            <span className="calendar-more-meals">
                                                +{dayMeals.length - 4}
                                            </span>
                                            )}
                                        </span>
                                        )}
                                        {isToday(day) && (
                                            <span className="today-label">Today</span>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                        <div className="calendar-meal-legend">
                        {["Breakfast", "Lunch", "Dinner", "Snack"].map((type) => (
                            <span key={type}>
                            <i
                                className={`calendar-meal-dot meal-type-${getMealTypeClass(type)}`}
                                aria-hidden="true"
                            />
                            {type}
                            </span>
                        ))}
                        </div>
                    </div>
                )}

                {/*Add week and day layouts*/}
                
                {/* Week View */}
                {view === "week" && (
                    <div className="calendar-week-grid">
                        {weekDays.map((day) => {
                            const key = getDateKey(day);
                            const dayMeals = meals
                            .filter((meal) => meal.date === key)
                            .map((meal) => {
                                const recipe = recipes.find(
                                (item) => String(item.id) === String(meal.recipeId)
                                );

                                return {
                                ...meal,
                                image: recipe?.image || meal.image || "",
                                };
                            });

                            return (
                                <button
                                    type="button"
                                    key={key}
                                    className={[
                                        "calendar-week-day",
                                        isSelected(day) ? "selected" : "",
                                        isToday(day) ? "today" : ""
                                    ].filter(Boolean).join(" ")}
                                    aria-label={`${key}: ${dayMeals.length} planned meals`}
                                    aria-pressed={isSelected(day)}
                                    onClick={() => selectDay(day)}
                                >
                                    <span className="week-day-name">
                                        {day.toLocaleDateString("en-US", {
                                            weekday: "short"
                                        })}
                                    </span>

                                    <span className="week-day-number">
                                        {day.getDate()}
                                    </span>


                                <span className="week-day-meals">
                                {dayMeals.length === 0 ? (
                                    <span className="no-meals">
                                    No meals
                                    </span>
                                ) : (
                                    dayMeals.map((meal, index) => (
                                    <span
                                        className={`week-meal meal-type-${getMealTypeClass(meal.type)}`}
                                        key={meal.id ?? `${key}-${index}`}
                                    >
                                        <span className="week-meal-thumb">
                                        {meal.image ? (
                                            <img src={meal.image} alt="" loading="lazy" />
                                        ) : (
                                            <span aria-hidden="true">✿</span>
                                        )}
                                        </span>

                                        <span className="week-meal-content">
                                        <small>{meal.type || "Meal"}</small>
                                        <strong>{meal.name}</strong>
                                        </span>
                                    </span>
                                    ))
                                )}
                                </span>

                                </button>
                            );
                        })}
                    </div>
                )}


                {/* ==========================================
                    DAY VIEW — FULL MEAL CARDS
                    ========================================== */}

                {view === "day" && (
                <section className="calendar-single-day">

                    {/* Date heading and navigation */}
                    <div className="calendar-day-header">
                    <span className="calendar-eyebrow">
                        DAILY MEAL PLAN
                    </span>

                    <h2>{selectedDateText}</h2>

                    <p>
                        {selectedMeals.length === 0
                        ? "No meals planned for this day yet."
                        : `${selectedMeals.length} meal${
                            selectedMeals.length === 1 ? "" : "s"
                            } planned`}
                    </p>

                    <div className="day-navigation">
                        <button
                        type="button"
                        onClick={goToPreviousMonth}
                        >
                        ← Previous day
                        </button>

                        <button
                        type="button"
                        onClick={goToNextMonth}
                        >
                        Next day →
                        </button>
                    </div>
                    </div>

                    {/* Day view widgets */}
                    <div className="calendar-day-dashboard calendar-day-dashboard--full">

                    {/* LEFT: Full meal cards */}
                    <section className="meals-selection">

                        <div className="meals-heading">
                        <div>
                            <span>YOUR DAILY MENU</span>
                            <h2>Planned Meals</h2>
                        </div>

                        <button
                            type="button"
                            className="add-meal-button"
                            disabled={loading || !!loadError}
                            onClick={() => setShowForm(true)}
                        >
                            + Add Meal
                        </button>
                        </div>

                        {showForm && (
                        <AddMealForm
                            key={selectedDateKey}
                            date={selectedDateKey}
                            onSave={saveMeal}
                            onCancel={() => setShowForm(false)}
                        />
                        )}

                        {actionError && (
                        <p role="alert">{actionError}</p>
                        )}

                        {loading ? (
                        <p role="status">Loading meals...</p>
                        ) : loadError ? (
                        <div role="alert">
                            <p>{loadError}</p>
                            <button
                            type="button"
                            onClick={() => {
                                setLoading(true);
                                setLoadError("");
                                setRevision((value) => value + 1);
                            }}
                            >
                            Retry meals
                            </button>
                        </div>
                        ) : selectedMeals.length > 0 ? (

                        <div className="meals-list">

                            {selectedMeals.map((meal) => (
                            <div
                                className="scheduled-meal-entry"
                                key={meal.id}
                            >
                                <MealCard
                                meal={meal}
                                variant="full"
                                />

                                <button
                                type="button"
                                className="remove-meal-button"
                                disabled={removing !== null}
                                onClick={() => deleteMeal(meal.id)}
                                aria-label={`Remove ${meal.name} from calendar`}
                                >
                                {removing === meal.id
                                    ? "Removing..."
                                    : "Remove meal"}
                                </button>
                            </div>
                            ))}

                        </div>

                        ) : (
                        <div className="empty-meals">
                            <h3>Nothing on the menu yet.</h3>
                            <p>
                            Choose a recipe to start planning your day.
                            </p>
                        </div>
                        )}

                    </section>

                    {/* RIGHT: Daily nutrition */}
                    <DailyMacroSummary
                        meals={selectedMeals}
                        loading={loading}
                        error={loadError || recipesError}
                    />

                    </div>
                </section>
                )}



                {/* Selected Day's Meals */}
                {view !== "day" && (
                <section className="calendar-day-dashboard">
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
                                    <div key={meal.id} className="scheduled-meal-entry">
                                    <MealCard
                                        meal={meal}
                                        variant={view === "day" ? "full" : "compact"}
                                    />

                                    <button
                                        type="button"
                                        className="remove-meal-button"
                                        disabled={removing !== null}
                                        onClick={() => deleteMeal(meal.id)}
                                        aria-label={`Remove ${meal.name} from calendar`}
                                    >
                                        {removing === meal.id ? "Removing..." : "Remove meal"}
                                    </button>
                                    </div>

                                ))}
                            </div>
                        ) : (

                            <div className="empty-meals">
                                <h3>No meals for this day.</h3>

                                <p>Add a meal to start planning your day.</p>

            
                            </div>
                        )}
                    </section>
                    <DailyMacroSummary
                    meals={selectedMeals}
                    loading={loading}
                    error={loadError || recipesError}
                    />
                </section>
                )}
            </section>   
        </main>
    );
}
export default Calendar;