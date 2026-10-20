import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import RecipeCard from '../../components/RecipeCard/RecipeCard';
import './Recipes.css';
import RecipeForm from './RecipeForm';
import { getRecipes, createRecipe, updateRecipe, removeRecipe } from '../../api/recipes';
import { filterRecipes } from './filterRecipes.js';

function Recipes() {
    const navigate = useNavigate();

    const categories = ['All', 'High Protein', 'Low Calorie', 'Keto', 'My Recipes'];

    const [activeCategory, setActiveCategory] = useState('All');
    const [search, setSearch] = useState('');
    
    const [recipes, setRecipes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showForm, setShowForm] = useState(false);
    const [editingRecipe, setEditingRecipe] = useState(null);
    const [deletingId, setDeletingId] = useState(null);
    const [reload, setReload] = useState(0);

    useEffect(() => {
        let active = true;
        getRecipes().then(data => {
            if (active) setRecipes(data);
        }).catch(err => {
            if (active) setError(err.message);
        }).finally(() => {
            if (active) setLoading(false);
        });
        return () => { active = false; };
    }, [reload]);

    async function saveRecipe(fields) {
        const saved = editingRecipe
            ? await updateRecipe(editingRecipe.id, fields)
            : await createRecipe(fields);
        setRecipes(current => editingRecipe
            ? current.map(recipe => recipe.id === saved.id ? saved : recipe)
            : [...current, saved]);
        setEditingRecipe(null);
        setSearch('');
        setActiveCategory('All');
        setError('');
        setShowForm(false);
    }

    async function deleteRecipe(id) {
        setDeletingId(id);
        setError('');
        try {
            await removeRecipe(id);
            setRecipes(current => current.filter(recipe => recipe.id !== id));
        } catch (err) {
            setError(err.message);
        } finally {
            setDeletingId(null);
        }
    }

    const filteredRecipes = filterRecipes(recipes, search, activeCategory);
    const hasFilters = search.trim() !== '' || activeCategory !== 'All';

    return (
        <main className="recipes-page">
            {/* Sidebar */}

            <aside className="recipes-sidebar">
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
                        className="nav-item active"
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

            {/* Main Content */}

            <section className="recipes-content">

                <header className="recipes-header">

                    <div>

                        <span className="recipes-eyebrow">
                            PANNED OUT
                        </span>

                        <h1>Recipes</h1>

                        <p>Discover and manage your favorite recipes.</p>
                    </div>

                    <button className="add-recipe-button" disabled={loading} onClick={() => { setEditingRecipe(null); setShowForm(true); }}>
                        + Add Recipe
                    </button>
                </header>

                {showForm && <RecipeForm key={editingRecipe?.id ?? "new"} recipe={editingRecipe} onSave={saveRecipe} onCancel={() => { setShowForm(false); setEditingRecipe(null); }} />}
                {loading && <p role="status">Loading recipes…</p>}
                {error && <div role="alert"><p>{error}</p><button onClick={() => { setLoading(true); setError(''); setReload(value => value + 1); }}>Retry loading recipes</button></div>}

                <div className="recipe-search">
                    <label htmlFor="recipe-search">Search recipes</label>
                    <input
                        id="recipe-search"
                        type="search"
                        placeholder="Search by recipe name"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                    />
                </div>

                {/*Categories */}
                <div className="recipes-categories">
                    {categories.map((category) => (
                        <button
                            key={category}
                            aria-pressed={activeCategory === category}
                            className={`category-button ${activeCategory === category ? 'active' : ''}`}
                            onClick={() => setActiveCategory(category)}
                        >
                            {category}
                        </button>
                    ))}
                </div>

                <p role="status" className="recipe-result-count" hidden={loading || !!error}>
                    {filteredRecipes.length} {filteredRecipes.length === 1 ? 'recipe' : 'recipes'} found
                </p>

                {/* Recipes List */}

                <section className="recipe-section">
                    <div className="section-heading">
                        <div> 
                            <span>
                                YOUR COLLECTION
                            </span>

                            <h2>
                                Recipes
                            </h2>

                        </div>
                    </div>

                    {loading ? null : filteredRecipes.length > 0 ? (
                        
                        <div className="recipe-grid">

                            {filteredRecipes.map((recipe) => (
                                <RecipeCard
                                    key={recipe.id}
                                    recipe={recipe}
                                    onEdit={recipe => { setEditingRecipe(recipe); setShowForm(true); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                                    onDelete={deleteRecipe}
                                    deleting={deletingId !== null}
                                />
                            ))}
                        </div>
                    ) : (

                        <div className="empty-recipes" hidden={!!error}>
                            <h3>No recipes found.</h3>

                            <p>{hasFilters
                                ? 'Try another recipe name or category, or clear your filters.'
                                : 'Start by adding your favorite recipes to your collection.'}</p>
                            {hasFilters ? (
                                <button className="add-recipe-button" onClick={() => {
                                    setSearch('');
                                    setActiveCategory('All');
                                }}>
                                    Clear filters
                                </button>
                            ) : (
                                <button className="add-recipe-button" disabled={loading} onClick={() => { setEditingRecipe(null); setShowForm(true); }}>
                                    + Add Recipe
                                </button>
                            )}
                        </div>
                    )}
                </section>

                {/* Meal Plans */}

                <section className="plans-section">
                    <div className="section-heading">
                        <div> 
                            <span>
                                CURATED FOR YOU
                            </span>

                            <h2>
                                Meal Plans
                            </h2>

                        </div>
                    </div>

                    <div className="plan-grid">

                        <div className="plan-card">
                            <span className="plan-icon">
                                🥑
                            </span>

                            <h3>
                                Keto Plan
                            </h3>

                            <p>
                                A low-carb, high-fat meal plan designed to help you achieve ketosis and maintain energy levels throughout the day.
                            </p>

                            <button>
                                Explore →
                            </button>
                        </div>

                        <div className="plan-card">
                            <span className="plan-icon">
                                🥗
                            </span>

                            <h3>
                                Low-Calorie Plan
                            </h3>

                            <p>
                                A meal plan focused on reducing calorie intake while ensuring balanced nutrition, helping you achieve your weight management goals.
                            </p>

                            <button>
                                Explore →
                            </button>
                        </div>

                        <div className="plan-card">
                            <span className="plan-icon">
                                💪
                            </span>

                            <h3>
                                High Protein Plan
                            </h3>

                            <p>
                                A meal plan rich in protein, designed to support muscle growth and repair, and maintain energy levels throughout the day.
                            </p>

                            <button>
                                Explore →
                            </button>
                        </div>
                    </div>
                </section>

            </section>

        </main>
    );
}

export default Recipes;
    