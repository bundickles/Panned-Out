
import "./DailyMacroSummary.css";

const macroFields = [
  { key: "protein", label: "Protein", kcalPerGram: 4 },
  { key: "carbohydrates", label: "Carbs", kcalPerGram: 4 },
  { key: "fat", label: "Fat", kcalPerGram: 9 },
];

export default function DailyMacroSummary({
  meals = [],
  loading = false,
  error = "",
}) {
  const knownMeals = meals.filter(
    (meal) => meal.nutritionAvailable
  );

  const totals = knownMeals.reduce(
    (sum, meal) => ({
      calories: sum.calories + Number(meal.calories),
      protein: sum.protein + Number(meal.protein),
      carbohydrates:
        sum.carbohydrates + Number(meal.carbohydrates),
      fat: sum.fat + Number(meal.fat),
    }),
    {
      calories: 0,
      protein: 0,
      carbohydrates: 0,
      fat: 0,
    }
  );

  const macroCalories =
    totals.protein * 4 +
    totals.carbohydrates * 4 +
    totals.fat * 9;

  const hasMissingNutrition =
    knownMeals.length < meals.length;

  const showValues =
    knownMeals.length > 0 || meals.length === 0;

  if (loading) {
    return (
      <aside className="macro-summary">
        <h2>Daily Nutrition</h2>
        <p role="status">Loading nutrition...</p>
      </aside>
    );
  }

  if (error) {
    return (
      <aside className="macro-summary">
        <h2>Daily Nutrition</h2>
        <p role="status">
          Nutrition information is currently unavailable.
        </p>
      </aside>
    );
  }

  return (
    <aside
      className="macro-summary"
      aria-label="Daily planned nutrition"
    >
      <span className="macro-eyebrow">YOUR DAILY TOTALS</span>
      <h2>Daily Nutrition</h2>

      <div className="macro-calories">
        <strong>
          {showValues
            ? Math.round(totals.calories).toLocaleString()
            : "—"}
        </strong>
        <span>planned calories</span>
      </div>

      <div className="macro-bars">
        {macroFields.map((macro) => (
          <div className={`macro-item macro-${macro.key}`}
               key={macro.key}>
            <div className="macro-label">
              <span>{macro.label}</span>
              <strong>
                {showValues
                  ? `${Math.round(totals[macro.key])} g`
                  : "—"}
              </strong>
            </div>

            <progress
              value={
                knownMeals.length > 0
                  ? totals[macro.key] * macro.kcalPerGram
                  : 0
              }
              max={Math.max(macroCalories, 1)}
              aria-label={`${macro.label} share of planned macro calories`}
            />
          </div>
        ))}
      </div>

      {hasMissingNutrition ? (
        <p className="macro-note">
          Nutrition available for {knownMeals.length} of{" "}
          {meals.length} planned meals. Totals are incomplete.
        </p>
      ) : (
        <p className="macro-note">
          Calculated from recipes planned for this day.
          Not a record of food consumed.
        </p>
      )}
    </aside>
  );
}
