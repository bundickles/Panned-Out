export const recipeSortOptions = [
    ['name-asc', 'Name: A–Z'], ['name-desc', 'Name: Z–A'],
    ['difficulty-asc', 'Difficulty: easy to hard'], ['difficulty-desc', 'Difficulty: hard to easy'],
    ['prepTime-asc', 'Prep time: shortest first'], ['prepTime-desc', 'Prep time: longest first'],
];
export function normalizeRecipeSort(value) {
    return recipeSortOptions.some(([key]) => key === value) ? value : 'name-asc';
}
const collator = new Intl.Collator('en', { sensitivity: 'base', numeric: true });
function valueFor(recipe, field) {
    if (field === 'name') return typeof recipe.name === 'string' && recipe.name.trim() ? recipe.name.trim() : null;
    if (field === 'difficulty') return ({ easy: 0, medium: 1, hard: 2 })[String(recipe.difficulty ?? '').trim().toLowerCase()] ?? null;
    const value = recipe.prepTime;
    return (typeof value === 'number' || typeof value === 'string') && String(value).trim() !== '' && Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : null;
}
export function sortRecipes(recipes, order) {
    const [field, direction] = normalizeRecipeSort(order).split('-');
    return (Array.isArray(recipes) ? recipes : []).filter(recipe => recipe && typeof recipe === 'object')
        .map((recipe, index) => ({ recipe, index, value: valueFor(recipe, field) }))
        .sort((a, b) => {
            if (a.value === null || b.value === null) return a.value === b.value ? a.index - b.index : a.value === null ? 1 : -1;
            const comparison = field === 'name' ? collator.compare(a.value, b.value) : a.value - b.value;
            return comparison * (direction === 'desc' ? -1 : 1) || a.index - b.index;
        }).map(({ recipe }) => recipe);
}
