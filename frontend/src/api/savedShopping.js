export function snapshotFields(snapshot) {
    const fields = { start: snapshot.start, end: snapshot.end, itemCount: String(snapshot.items.length), warningCount: String(snapshot.warnings.length) };
    snapshot.items.forEach((item, i) => {
        const p = `item.${i}.`;
        fields[p+'text'] = item.name;
        fields[p+'occurrences'] = String(item.occurrences);
        fields[p+'sourceCount'] = String(item.sources.length);
        item.sources.forEach((source,j) => {
            fields[`${p}source.${j}.mealId`] = source.mealId;
            fields[`${p}source.${j}.recipeId`] = String(source.recipeId);
        });
    });
    snapshot.warnings.forEach((warning,i) => {
        fields[`warning.${i}.message`] = warning.message;
        fields[`warning.${i}.mealId`] = warning.source.mealId;
        fields[`warning.${i}.recipeId`] = String(warning.source.recipeId);
    });
    return fields;
}

async function request(path='', options={}) {
    let response;
    try { response=await fetch(`/api/shopping-lists${path}`, { ...options, credentials:'same-origin', headers:{'X-Panned-Out-Request':'1'} }); }
    catch(error) { if(error.name==='AbortError') throw error; throw new Error('Cannot reach saved shopping lists. Please try again.'); }
    if(response.status===401) window.dispatchEvent(new Event('panned-session-expired'));
    let data;
    try { data=await response.json(); } catch { throw new Error('The saved-list service is unavailable. Please try again.'); }
    if(!response.ok) throw new Error(data.error || 'Unable to update the saved shopping list. Please try again.');
    return data;
}
export const getSavedLists = (options={}) => request('',options);
export const getSavedList = (id,options={}) => request(`/${encodeURIComponent(id)}`,options);
export const saveShoppingList = snapshot => request('',{method:'POST',body:new URLSearchParams(snapshotFields(snapshot))});
export const setItemPurchased = (listId,itemId,purchased) => request(`/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}/purchased`,{method:'PATCH',body:new URLSearchParams({purchased:String(purchased)})});
