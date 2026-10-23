
import { useState } from "react";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import "./MealPlans.css";

// Built-in dietary collections
const presetPlans = [
  {
    id: "high-protein",
    name: "High Protein",
    category: "NOURISH",
    description: "Hearty, protein-rich meals to fuel your day.",
    icon: "🥚",
    type: "preset",
  },
  {
    id: "low-calorie",
    name: "Low Calorie",
    category: "FRESH",
    description: "Lighter meals without sacrificing flavor.",
    icon: "🥗",
    type: "preset",
  },
  {
    id: "keto",
    name: "Keto",
    category: "LOW CARB",
    description: "Low-carb meals with rich, satisfying flavors.",
    icon: "🥑",
    type: "preset",
  },
  {
    id: "balanced",
    name: "Balanced",
    category: "EVERYDAY",
    description: "A little bit of everything for everyday eating.",
    icon: "🍲",
    type: "preset",
  },
];

function MealPlans() {
  // Load saved custom plans when the page first renders.
  const [customPlans, setCustomPlans] = useState(() => {
    try {
      const saved = JSON.parse(
        localStorage.getItem("pannedOutCustomPlans") || "[]"
      );

      return Array.isArray(saved) ? saved : [];
    } catch {
      return [];
    }
  });

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [planName, setPlanName] = useState("");
  const [planDescription, setPlanDescription] = useState("");

  // Save custom plans to the browser.
  function saveCustomPlans(updatedPlans) {
    setCustomPlans(updatedPlans);
    localStorage.setItem(
      "pannedOutCustomPlans",
      JSON.stringify(updatedPlans)
    );
  }

  // Create a custom plan.
  function handleCreatePlan(event) {
    event.preventDefault();

    if (!planName.trim()) return;

    const newPlan = {
      id: crypto.randomUUID(),
      name: planName.trim(),
      category: "CUSTOM COLLECTION",
      description:
        planDescription.trim() ||
        "A personalized meal plan made just for you.",
      icon: "📖",
      type: "custom",
    };

    saveCustomPlans([...customPlans, newPlan]);

    setPlanName("");
    setPlanDescription("");
    setShowCreateForm(false);
  }

  // Delete a custom plan.
  function handleDeletePlan(id) {
    const updatedPlans = customPlans.filter(
      (plan) => plan.id !== id
    );

    saveCustomPlans(updatedPlans);
    setSelectedPlan(null);
  }

  // Reusable plan card.
  function renderPlanCard(plan) {
    return (
      <button
        key={plan.id}
        type="button"
        className="meal-plan-card"
        onClick={() => setSelectedPlan(plan)}
      >
        <div className="meal-plan-card-top">
          <span className="meal-plan-category">
            {plan.category}
          </span>
          <span className="meal-plan-leaf">✦</span>
        </div>

        <div className="meal-plan-art">
          <span>{plan.icon}</span>
        </div>

        <div className="meal-plan-card-body">
          <h3>{plan.name}</h3>
          <p>{plan.description}</p>

          <span className="meal-plan-explore">
            Explore Plan →
          </span>
        </div>
      </button>
    );
  }

  return (
    <main className="meal-plans-page">
      <Sidebar />

      <section className="meal-plans-content">
        <div className="meal-plans-container">

          {/* Introductory banner */}
          <header className="meal-plans-hero">
            <span className="meal-plans-eyebrow">
              THE PANNED OUT COLLECTION
            </span>

            <h1>Find Your Perfect Plate</h1>

            <p>
              A little inspiration for every appetite.
              Explore a collection or create a meal plan
              that feels like home.
            </p>

            <span className="meal-plans-hero-footer">
              ✦ Made for your table
            </span>
          </header>

          {/* Preset collections */}
          <div className="meal-plans-section-heading">
            <div>
              <span className="meal-plans-section-label">
                CURATED FOR YOU
              </span>
              <h2>Explore Meal Plans</h2>
            </div>

            <span className="meal-plans-count">
              {presetPlans.length} collections
            </span>
          </div>

          <div className="meal-plans-grid">
            {presetPlans.map(renderPlanCard)}
          </div>

          {/* Custom plans */}
          <div className="meal-plans-section-heading custom-heading">
            <div>
              <span className="meal-plans-section-label">
                YOUR OWN CREATIONS
              </span>
              <h2>My Meal Plans</h2>
            </div>

            <button
              type="button"
              className="create-plan-button"
              onClick={() => setShowCreateForm(true)}
            >
              + Create New Plan
            </button>
          </div>

          {customPlans.length > 0 ? (
            <div className="meal-plans-grid">
              {customPlans.map(renderPlanCard)}
            </div>
          ) : (
            <div className="meal-plans-empty">
              <span className="empty-book-icon">📖</span>

              <h3>Your collection starts here.</h3>

              <p>
                Create a personalized meal plan and
                make it your own.
              </p>

              <button
                type="button"
                onClick={() => setShowCreateForm(true)}
              >
                Create Your First Plan
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Create plan modal */}
      {showCreateForm && (
        <div
          className="meal-plan-modal-overlay"
          onClick={() => setShowCreateForm(false)}
        >
          <div
            className="meal-plan-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-plan-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              type="button"
              aria-label="Close"
              onClick={() => setShowCreateForm(false)}
            >
              ×
            </button>

            <span className="meal-plans-section-label">
              A NEW COLLECTION
            </span>

            <h2 id="create-plan-title">
              Create Your Meal Plan
            </h2>

            <p>
              Give your collection a name and tell us
              a little about it.
            </p>

            <form onSubmit={handleCreatePlan}>
              <label htmlFor="plan-name">
                Plan Name
              </label>

              <input
                id="plan-name"
                type="text"
                placeholder="e.g. My Weekly Favorites"
                value={planName}
                maxLength={60}
                required
                onChange={(event) =>
                  setPlanName(event.target.value)
                }
              />

              <label htmlFor="plan-description">
                Description
              </label>

              <textarea
                id="plan-description"
                placeholder="What makes this plan special?"
                value={planDescription}
                maxLength={300}
                onChange={(event) =>
                  setPlanDescription(event.target.value)
                }
              />

              <div className="modal-actions">
                <button
                  type="button"
                  className="modal-cancel"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="modal-submit"
                >
                  Create Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Selected plan details */}
      {selectedPlan && (
        <div
          className="meal-plan-modal-overlay"
          onClick={() => setSelectedPlan(null)}
        >
          <div
            className="meal-plan-modal plan-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="plan-detail-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              type="button"
              aria-label="Close"
              onClick={() => setSelectedPlan(null)}
            >
              ×
            </button>

            <div className="detail-plan-icon">
              {selectedPlan.icon}
            </div>

            <span className="meal-plans-section-label">
              {selectedPlan.category}
            </span>

            <h2 id="plan-detail-title">
              {selectedPlan.name}
            </h2>

            <p>{selectedPlan.description}</p>

            <div className="plan-detail-note">
              Recipe selection and calendar scheduling
              will be added in the next step.
            </div>

            {selectedPlan.type === "custom" && (
              <button
                type="button"
                className="delete-plan-button"
                onClick={() =>
                  handleDeletePlan(selectedPlan.id)
                }
              >
                Delete This Plan
              </button>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

export default MealPlans;
