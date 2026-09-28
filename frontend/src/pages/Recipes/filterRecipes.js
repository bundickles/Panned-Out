export function filterRecipes(recipes, search = '', category = 'All') {
    if (!Array.isArray(recipes)) return [];

    const query = typeof search === 'string' ? search.trim().toLowerCase() : '';

    return recipes.filter((recipe) => {
        if (!recipe || typeof recipe !== 'object' || Array.isArray(recipe)) return false;
        const name = typeof recipe.name === 'string' ? recipe.name : '';
        return name.toLowerCase().includes(query)
            && (category === 'All' || recipe.category === category);
    });
}
