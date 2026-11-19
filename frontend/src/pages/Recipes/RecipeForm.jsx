
import { useEffect, useRef, useState } from "react";

export default function RecipeForm({ recipe, onSave, onCancel }) {
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    // Image preview state
    const [imagePreview, setImagePreview] = useState("");
    const imageInputRef = useRef(null);

    // Clean up temporary preview URLs when they change
    // or when the component unmounts.
    useEffect(() => {
        return () => {
            if (imagePreview) {
                URL.revokeObjectURL(imagePreview);
            }
        };
    }, [imagePreview]);

    // Clear the image preview and reset file input.
    function clearImage() {
        setImagePreview("");

        if (imageInputRef.current) {
            imageInputRef.current.value = "";
        }
    }

    // Validate the selected image and display a preview.
    function handleImageChange(event) {
        const file = event.target.files?.[0];

        if (!file) {
            clearImage();
            return;
        }

        if (!file.type.startsWith("image/")) {
            setError("Please select an image file.");
            clearImage();
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            setError("Image must be 5 MB or smaller.");
            clearImage();
            return;
        }

        setError("");
        setImagePreview(URL.createObjectURL(file));
    }

    // Submit recipe details.
    async function submit(event) {
        event.preventDefault();

        const fields = Object.fromEntries(
            new FormData(event.currentTarget)
        );

        setSaving(true);
        setError("");

        try {
            await onSave(fields);
        } catch (err) {
            setError(err.message || "Unable to save recipe.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <form
            className="recipe-form"
            onSubmit={submit}
            aria-labelledby="recipe-form-title"
        >
            <h2 id="recipe-form-title">
                {recipe ? "Edit Recipe" : "Add Recipe"}
            </h2>

            <fieldset disabled={saving}>

                {/* Recipe name */}
                <label>
                    Recipe name
                    <input
                        name="name"
                        defaultValue={recipe?.name ?? ""}
                        required
                        maxLength={200}
                        autoFocus
                    />
                </label>

                {/* Recipe category */}
                <label>
                    Category
                    <select
                        name="category"
                        defaultValue={recipe?.category ?? "My Recipes"}
                    >
                        {[
                            "My Recipes",
                            "High Protein",
                            "Low Calorie",
                            "Keto",
                        ].map((value) => (
                            <option key={value} value={value}>
                                {value}
                            </option>
                        ))}
                    </select>
                </label>

                {/* Difficulty */}
                <label>
                    Difficulty
                    <select
                        name="difficulty"
                        defaultValue={recipe?.difficulty ?? "Easy"}
                    >
                        {["Easy", "Medium", "Hard"].map((value) => (
                            <option key={value} value={value}>
                                {value}
                            </option>
                        ))}
                    </select>
                </label>

                {/* Meal type */}
                <label>
                    Meal type
                    <select
                        name="mealType"
                        defaultValue={recipe?.mealType ?? "Breakfast"}
                    >
                        {[
                            "Breakfast",
                            "Lunch",
                            "Dinner",
                            "Snack",
                        ].map((value) => (
                            <option key={value} value={value}>
                                {value}
                            </option>
                        ))}
                    </select>
                </label>

                {/* Ingredients */}
                <label>
                    Ingredients
                    <textarea
                        name="ingredients"
                        defaultValue={recipe?.ingredients ?? ""}
                        required
                        maxLength={10000}
                        rows={3}
                    />
                </label>

                {/* Instructions */}
                <label>
                    Instructions
                    <textarea
                        name="instructions"
                        defaultValue={recipe?.instructions ?? ""}
                        required
                        maxLength={10000}
                        rows={3}
                    />
                </label>

                {/* Numeric recipe information */}
                <div className="recipe-form-numbers">
                    {[
                        ["prepTime", "Prep time (minutes)"],
                        ["calories", "Calories"],
                        ["protein", "Protein (g)"],
                        ["fat", "Fat (g)"],
                        ["carbohydrates", "Carbohydrates (g)"],
                        ["fiber", "Fiber (g)"],
                    ].map(([name, label]) => (
                        <label key={name}>
                            {label}
                            <input
                                name={name}
                                type="number"
                                min="0"
                                max="100000"
                                step="1"
                                defaultValue={recipe?.[name] ?? 0}
                                required
                            />
                        </label>
                    ))}
                </div>

                {/* Image selection */}
                <label>
                    Recipe image (optional)
                    <input
                        ref={imageInputRef}
                        type="file"
                        accept="image/*"
                        onChange={handleImageChange}
                    />
                </label>

                {/* Image preview */}
                {imagePreview && (
                    <div className="recipe-form-image-preview">
                        <img
                            src={imagePreview}
                            alt="Recipe preview"
                        />

                        <button
                            type="button"
                            onClick={clearImage}
                        >
                            Remove image
                        </button>
                    </div>
                )}

                {/* Form buttons */}
                <button
                    className="add-recipe-button"
                    type="submit"
                >
                    {saving ? "Saving…" : "Save recipe"}
                </button>

                <button
                    type="button"
                    onClick={onCancel}
                >
                    Cancel
                </button>

            </fieldset>

            {error && (
                <p role="alert">{error}</p>
            )}
        </form>
    );
}
