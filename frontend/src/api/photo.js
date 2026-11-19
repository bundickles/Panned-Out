const ENDPOINT = '/api/ai/photo-recipe';
export const PHOTO_MAX_BYTES = 5 * 1024 * 1024;
export const PHOTO_TYPES = ['image/jpeg', 'image/png'];
export function validatePhoto(file) {
    if (!file || !PHOTO_TYPES.includes(file.type)) throw new Error('Choose a JPEG or PNG image.');
    if (!file.size) throw new Error('The photo is empty. Choose another image.');
    if (file.size > PHOTO_MAX_BYTES) throw new Error('Choose an image no larger than 5 MB.');
}
async function request(options) {
    let response;
    try { response = await fetch(ENDPOINT, { credentials: 'same-origin', ...options }); }
    catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new Error('Cannot reach photo recognition. Please try again.');
    }
    if (response.status === 401) window.dispatchEvent(new Event('panned-session-expired'));
    let result;
    try { result = await response.json(); }
    catch { throw new Error('Photo recognition is unavailable. Please try again.'); }
    if (!response.ok) throw new Error(result.error || 'Unable to analyze this photo. Please try again.');
    return result;
}
export async function getPhotoAvailability(signal) {
    const result = await request({ signal });
    if (typeof result.available !== 'boolean') throw new Error('Photo recognition is unavailable. Please try again.');
    return result.available;
}
export async function analyzePhoto(file, signal) {
    validatePhoto(file);
    const result = await request({method:'POST',headers:{'Content-Type':file.type,'X-Panned-Out-Request':'1'},body:file,signal});
    if (result.status === 'no_result') return {status:'no_result',message:typeof result.message === 'string' ? result.message : 'No recognizable food was found. Try a clearer food photo.'};
    const recipe=result.recipe;
    const lines = value => Array.isArray(value) && value.length > 0 && value.length <= 100 && value.every(line=>typeof line==='string' && line.trim()) && value.join('\n').length <= 10000;
    if (result.status !== 'success' || result.requiresConfirmation !== true || !recipe || typeof recipe.name !== 'string' || !recipe.name.trim() || recipe.name.length>200 || !lines(recipe.ingredients) || !lines(recipe.steps))
        throw new Error('Photo recognition returned an incomplete recipe. Please try again.');
    return {status:'success',recipe:{name:recipe.name,ingredients:recipe.ingredients.join('\n'),instructions:recipe.steps.join('\n'),category:'My Recipes',difficulty:'Easy',mealType:'Dinner'},warnings:Array.isArray(result.warnings) ? result.warnings.filter(value=>typeof value==='string') : []};
}
