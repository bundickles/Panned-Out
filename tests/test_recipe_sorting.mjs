import test from 'node:test';
import assert from 'node:assert/strict';
import { sortRecipes, normalizeRecipeSort } from '../frontend/src/pages/Recipes/sortRecipes.js';
import { filterRecipes } from '../frontend/src/pages/Recipes/filterRecipes.js';
const records = Object.freeze([
    Object.freeze({ id: 1, name: 'Zulu', difficulty: 'Hard', prepTime: 20, category: 'Keto' }),
    Object.freeze({ id: 2, name: 'alpha', difficulty: ' Easy ', prepTime: 0, category: 'Keto' }),
    Object.freeze({ id: 3, name: 'Beta', difficulty: 'medium', prepTime: '10', category: 'My Recipes' }),
    Object.freeze({ id: 4, name: 'Beta', difficulty: 'unknown', prepTime: null, category: 'Keto' }),
]);
const ids = order => sortRecipes(records, order).map(r => r.id);
test('all six orders and stable ties', () => {
    assert.deepEqual(ids('name-asc'), [2, 3, 4, 1]);
    assert.deepEqual(ids('name-desc'), [1, 3, 4, 2]);
    assert.deepEqual(ids('difficulty-asc'), [2, 3, 1, 4]);
    assert.deepEqual(ids('difficulty-desc'), [1, 3, 2, 4]);
    assert.deepEqual(ids('prepTime-asc'), [2, 3, 1, 4]);
    assert.deepEqual(ids('prepTime-desc'), [1, 3, 2, 4]);
    assert.deepEqual(records.map(r => r.id), [1, 2, 3, 4]);
});
test('missing and invalid values stay last in either direction; zero is valid', () => {
    const data = [{ id: 1 }, { id: 2, prepTime: -1 }, { id: 3, prepTime: '' }, { id: 4, prepTime: 0 }, { id: 5, prepTime: false }];
    for (const order of ['prepTime-asc', 'prepTime-desc']) assert.deepEqual(sortRecipes(data, order).map(r => r.id), [4, 1, 2, 3, 5]);
    assert.deepEqual(sortRecipes(null), []);
    assert.equal(normalizeRecipeSort('invalid'), 'name-asc');
});
test('sorting composes with search and categories without restoring excluded recipes', () => {
    assert.deepEqual(sortRecipes(filterRecipes(records, '', 'Keto'), 'name-desc').map(r => r.id), [1, 4, 2]);
    assert.deepEqual(sortRecipes(filterRecipes(records, 'beta'), 'prepTime-asc').map(r => r.id), [3, 4]);
});
