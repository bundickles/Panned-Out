import "./ThemeArt.css";

const PLAN_IDS = new Set(["high-protein", "low-calorie", "keto", "balanced"]);

/** Illustration for the existing four preset plans and any custom plan. */
export default function PlanArtwork({ plan }) {
  const name = plan?.type === "custom" || !PLAN_IDS.has(plan?.id)
    ? "custom"
    : plan.id;
  return (
    <img
      className="po-plan-art-image"
      src={`/theme-art/meal-plans/${name}.png`}
      alt=""
      aria-hidden="true"
      draggable="false"
    />
  );
}
