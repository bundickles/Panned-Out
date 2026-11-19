import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzePhoto, getPhotoAvailability } from '../../api/photo';
import { createRecipe } from '../../api/recipes';
import RecipeForm from '../../pages/Recipes/RecipeForm';
import './PhotoRecipeStudio.css';

export default function PhotoRecipeStudio({ file }) {
    const navigate=useNavigate();
    const [service,setService]=useState(null);
    const [revision,setRevision]=useState(0);
    const [busy,setBusy]=useState(false);
    const [error,setError]=useState('');
    const [result,setResult]=useState(null);
    const [reviewed,setReviewed]=useState(false);
    const lifecycle=useRef({alive:false,sequence:0,controller:null});
    useEffect(()=>{
        const state=lifecycle.current;
        state.alive=true;
        return ()=>{state.alive=false;state.sequence++;state.controller?.abort();};
    },[]);
    useEffect(()=>{
        const request=new AbortController();
        getPhotoAvailability(request.signal).then(available=>{if(!request.signal.aborted)setService({revision,available});})
            .catch(error=>{if(!request.signal.aborted)setService({revision,error:error.message});});
        return ()=>request.abort();
    },[revision]);
    function cancel() {
        lifecycle.current.sequence++;lifecycle.current.controller?.abort();setBusy(false);
    }
    async function analyze() {
        const id=++lifecycle.current.sequence;
        lifecycle.current.controller?.abort();
        const request=new AbortController();lifecycle.current.controller=request;
        setBusy(true);setError('');setResult(null);setReviewed(false);
        try {
            const data=await analyzePhoto(file,request.signal);
            if(lifecycle.current.alive && lifecycle.current.sequence===id)setResult(data);
        } catch(error) {
            if(lifecycle.current.alive && lifecycle.current.sequence===id && error.name!=='AbortError')setError(error.message);
        } finally {if(lifecycle.current.alive && lifecycle.current.sequence===id)setBusy(false);}
    }
    async function save(fields) {
        if(!reviewed)throw new Error('Review the ingredients and instructions, then check the confirmation before saving.');
        const saved=await createRecipe(fields);
        if(lifecycle.current.alive)navigate(`/recipes/${saved.id}`);
    }
    const connection=service?.revision===revision ? service : null;
    return <section className="photo-recipe-studio" aria-label="AI photo recipe">
        <h3>Turn this photo into a recipe idea</h3>
        <p>Your photo will be sent to Google Gemini only when you choose Analyze photo. AI may miss ingredients or allergens; review the suggestion before cooking or saving.</p>
        {!connection ? <p role="status">Checking photo service…</p> : connection.error ? <div role="alert">{connection.error}<button className="ai-photo-button" onClick={()=>setRevision(value=>value+1)}>Retry photo connection</button></div> : !connection.available && <p role="status">Photo recognition is not configured yet. The rest of the app is still available.</p>}
        <button className="ai-photo-button ai-photo-button-primary" type="button" disabled={!connection?.available || busy} onClick={analyze}>{busy ? 'Analyzing photo…' : 'Analyze photo'}</button>
        {busy && <><p role="status">Looking at your food photo. This may take up to 30 seconds.</p><button className="ai-photo-button" type="button" onClick={cancel}>Cancel analysis</button></>}
        {error && <p role="alert">{error} You can choose Analyze photo to retry.</p>}
        {result?.status==='no_result' && <p role="status">{result.message}</p>}
        {result?.status==='success' && <section aria-label="Review generated recipe">
            <h3>Review your recipe draft</h3>
            {result.warnings.length>0 && <ul>{result.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul>}
            <p>Check the suggested quantities and instructions. Prep time and nutrition are unknown; the form starts at zero so you can enter your own values. Photos are not saved with the recipe.</p>
            <label className="photo-recipe-review"><input type="checkbox" checked={reviewed} onChange={event=>setReviewed(event.target.checked)} />I reviewed the ingredients and instructions.</label>
            <RecipeForm recipe={result.recipe} onSave={save} onCancel={()=>{setResult(null);setReviewed(false);}} />
        </section>}
    </section>;
}
