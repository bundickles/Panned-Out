import { useEffect, useState } from 'react';

export default function RecipeForm({ onSave, onCancel }) {
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    //For adding image to recipecards
    const [imageFile, setImageFile] = useState(null);
    const [imagePreview, setImagePreview] = useState('');

    useEffect(() => {
    if (!imageFile) {
        setImagePreview('');
        return;
    }

    const previewUrl = URL.createObjectURL(imageFile);
        setImagePreview(previewUrl);

        return () => URL.revokeObjectURL(previewUrl);
    }, [imageFile]);
    async function submit(event) {
        event.preventDefault();
        const fields = Object.fromEntries(new FormData(event.currentTarget));
        setSaving(true);
        setError('');
        try {
            await onSave(fields);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    }
    return (
        <form className="recipe-form" onSubmit={submit} aria-labelledby="recipe-form-title">
            <h2 id="recipe-form-title">Add Recipe</h2>
            <fieldset disabled={saving}>
                <label>Recipe name<input name="name" required maxLength={200} autoFocus /></label>
                <label>Category<select name="category" defaultValue="My Recipes">
                    {['My Recipes', 'High Protein', 'Low Calorie', 'Keto'].map(value => <option key={value}>{value}</option>)}
                </select></label>
                <label>Difficulty<select name="difficulty">
                    {['Easy', 'Medium', 'Hard'].map(value => <option key={value}>{value}</option>)}
                </select></label>
                <label>Meal type<select name="mealType">
                    {['Breakfast', 'Lunch', 'Dinner', 'Snack'].map(value => <option key={value}>{value}</option>)}
                </select></label>
                <label>Ingredients<textarea name="ingredients" required maxLength={10000} rows={3} /></label>
                <label>Instructions<textarea name="instructions" required maxLength={10000} rows={3} /></label>
                <div className="recipe-form-numbers">
                    {[['prepTime', 'Prep time (minutes)'], ['calories', 'Calories'], ['protein', 'Protein (g)'],
                        ['fat', 'Fat (g)'], ['carbohydrates', 'Carbohydrates (g)'], ['fiber', 'Fiber (g)']].map(([name, label]) => (
                        <label key={name}>{label}<input name={name} type="number" min="0" max="100000" step="1" defaultValue="0" required /></label>
                    ))}
                </div>
                <label>
                    Recipe image (optional)
                    <input
                        type="file"
                        accept="image/*"
                        onChange={(event) => {
                            const file = event.target.files?.[0];

                            if (!file) {
                                setImageFile(null);
                                return;
                            }

                            if (!file.type.startsWith('image/')) {
                                setError('Please select an image file.');
                                event.target.value = '';
                                setImageFile(null);
                                return;
                            }

                            if (file.size > 5 * 1024 * 1024) {
                                setError('Image must be 5 MB or smaller.');
                                event.target.value = '';
                                setImageFile(null);
                                return;
                            }

                            setError('');
                            setImageFile(file);
                        }}
                    />
                </label>

                {imagePreview && (
                    <div className="recipe-form-image-preview">
                        <img src={imagePreview} alt="Recipe preview" />
                        <button
                            type="button"
                            onClick={() => setImageFile(null)}
                            >
                            Remove image
                        </button>
                    </div>
                )}
                <button className="add-recipe-button" type="submit">{saving ? 'Saving…' : 'Save recipe'}</button>
                <button type="button" onClick={onCancel}>Cancel</button>
            </fieldset>
            {error && <p role="alert">{error}</p>}
        </form>
    );
}
