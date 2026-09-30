import test from 'node:test';
import assert from 'node:assert/strict';
import { filterRecipes } from '../frontend/src/pages/Recipes/filterRecipes.js';

const recipes = Object.freeze([
    Object.freeze({ id: 1, name: 'Chicken Soup', category: 'High Protein' }),
    Object.freeze({ id: 2, name: 'Chicken Salad', category: 'Low Calorie' }),
    Object.freeze({ id: 3, name: 'Taco Bowl', category: 'Keto' }),
]);
const ids = (search, category) => filterRecipes(recipes, search, category).map(recipe => recipe.id);

test('exact, partial, case-insensitive, and trimmed search', () => {
    assert.deepEqual(ids('Chicken Soup'), [1]);
    assert.deepEqual(ids('chick'), [1, 2]);
    assert.deepEqual(ids(' CHICKEN '), [1, 2]);
    assert.deepEqual(ids('missing'), []);
    assert.deepEqual(ids(''), [1, 2, 3]);
    assert.deepEqual(ids('   '), [1, 2, 3]);
});

test('category can be applied, changed, cleared, and have no matches', () => {
    assert.deepEqual(ids('', 'Keto'), [3]);
    assert.deepEqual(ids('', 'Low Calorie'), [2]);
    assert.deepEqual(ids('', 'All'), [1, 2, 3]);
    assert.deepEqual(ids('', 'My Recipes'), []);
});

test('search and category combine, and each can be cleared independently', () => {
    assert.deepEqual(ids('chicken', 'Low Calorie'), [2]);
    assert.deepEqual(ids('chicken', 'Keto'), []);
    assert.deepEqual(ids('', 'Keto'), [3]);
    assert.deepEqual(ids('chicken', 'All'), [1, 2]);
});

test('missing data never crashes filtering', () => {
    for (const data of [null, undefined, [], {}]) {
        assert.deepEqual(filterRecipes(data), []);
    }
    const partial = [null, undefined, {}, { name: 'Soup' }, { category: 'Keto' }];
    assert.equal(filterRecipes(partial).length, 3);
    assert.deepEqual(filterRecipes(partial, 'soup'), [{ name: 'Soup' }]);
    assert.deepEqual(filterRecipes(partial, '', 'Keto'), [{ category: 'Keto' }]);
});

test('filtering preserves original records and reflects data changes', () => {
    assert.equal(filterRecipes(recipes, 'soup')[0], recipes[0]);
    const updated = [{ ...recipes[0], name: 'Vegetable Soup', category: 'Low Calorie' }];
    assert.equal(filterRecipes(updated, 'chicken').length, 0);
    assert.equal(filterRecipes(updated, 'vegetable', 'Low Calorie').length, 1);
    assert.equal(recipes[0].name, 'Chicken Soup');
});
