import test from 'node:test';
import assert from 'node:assert/strict';
import { snapshotFields } from '../frontend/src/api/savedShopping.js';
test('generated data maps to the saved-list form contract without trusting server IDs or flags',()=>{
 const source={mealId:'meal-id',recipeId:7,recipeName:'Rice bowl',date:'2030-01-01'};
 const snapshot={start:'2030-01-01',end:'2030-01-02',items:[{name:'米 & beans',occurrences:1,sources:[source],id:'untrusted',purchased:true}],warnings:[{message:'Missing recipe',source}]};
 const original=JSON.stringify(snapshot);const fields=snapshotFields(snapshot);
 assert.equal(fields['item.0.text'],'米 & beans');assert.equal(fields['item.0.source.0.recipeId'],'7');assert.equal(fields['warning.0.mealId'],'meal-id');assert.equal(fields.warningCount,'1');assert.equal(fields.itemCount,'1');
 assert.equal(fields['item.0.id'],undefined);assert.equal(fields['item.0.purchased'],undefined);assert.equal(JSON.stringify(snapshot),original);
});
test('empty snapshots preserve their date range and zero counts',()=>{assert.deepEqual(snapshotFields({start:'2030-01-01',end:'2030-01-01',items:[],warnings:[]}),{start:'2030-01-01',end:'2030-01-01',itemCount:'0',warningCount:'0'});});
