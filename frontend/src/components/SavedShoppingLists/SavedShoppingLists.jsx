import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { getSavedLists, getSavedList, saveShoppingList, setItemPurchased, deleteSavedList } from '../../api/savedShopping';
import './SavedShoppingLists.css';

export default function SavedShoppingLists({ generated }) {
    const { user } = useAuth();
    const [params,setParams] = useSearchParams();
    const selected=params.get('savedList') || '';
    const [revision,setRevision]=useState(0);
    const [directory,setDirectory]=useState(null);
    const [result,setResult]=useState(null);
    const [confirmDelete,setConfirmDelete]=useState(null);
    const [notice,setNotice]=useState('');
    const [busy,setBusy]=useState(false);
    const [action,setAction]=useState(null);
    const alive=useRef(false);
    const scope=useRef(null);
    const key=`${user.id}:${selected}:${revision}`;
    const directoryKey=`${user.id}:${revision}`;
    useLayoutEffect(()=>{scope.current={key,generated};},[key,generated]);
    useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
    useEffect(()=>{
        let active=true;
        getSavedLists().then(data=>{if(active)setDirectory({key:directoryKey,data});})
            .catch(error=>{if(active)setDirectory({key:directoryKey,error:error.message});});
        return()=>{active=false;};
    },[directoryKey]);
    useEffect(()=>{
        if(!selected)return;
        let active=true;
        getSavedList(selected).then(data=>{if(active)setResult({key,data});})
            .catch(error=>{if(active)setResult({key,error:error.message});});
        return()=>{active=false;};
    },[key,selected]);
    const lists=directory?.key===directoryKey ? directory : null;
    const current=result?.key===key ? result : null;
    const saved=current?.data;
    const error=action?.key===key ? action : null;
    function open(id) { const next=new URLSearchParams(params);next.set('savedList',id);setParams(next);setAction(null);setConfirmDelete(null);setNotice(''); }
    async function save() {
        const snapshot=generated;
        if(!snapshot)return;
        setBusy(true);setAction(null);
        try {
            const data=await saveShoppingList(snapshot);
            if(alive.current && scope.current.generated===snapshot) {setRevision(value=>value+1);open(data.id);}
        } catch(error) {if(alive.current && scope.current.generated===snapshot)setAction({key,message:error.message});}
        finally {if(alive.current)setBusy(false);}
    }
    async function purchased(itemId,value) {
        const operationKey=key;
        setBusy(true);setAction(null);
        try {
            const data=await setItemPurchased(selected,itemId,value);
            if(alive.current && scope.current.key===operationKey)setResult({key:operationKey,data});
        } catch(error) {
            if(alive.current && scope.current.key===operationKey)setAction({key:operationKey,message:error.message,retry:{itemId,value}});
        } finally {if(alive.current)setBusy(false);}
    }
    async function remove() {
        const operationKey=key;
        setBusy(true);setAction(null);
        try {
            await deleteSavedList(selected);
            if(alive.current && scope.current.key===operationKey) {
                const next=new URLSearchParams(params);
                next.delete('savedList');
                setParams(next, {replace:true});
                setRevision(value=>value+1);
                setConfirmDelete(null);
                setNotice('Saved shopping list deleted.');
            }
        } catch(error) {
            if(alive.current && scope.current.key===operationKey)setAction({key:operationKey,message:error.message});
        } finally {if(alive.current)setBusy(false);}
    }
    return <section className="saved-shopping-lists" aria-label="Saved shopping lists">
        <h2>Saved Shopping Lists</h2>
        <p>Save a snapshot to keep your list and purchased checkmarks after refresh or sign-in.</p>
        <button className="shopping-primary" type="button" disabled={!generated || busy} onClick={save}>{busy ? 'Working…' : 'Save generated list'}</button>
        {busy && <p role="status">Updating saved lists…</p>}
        {notice && <p role="status">{notice}</p>}
        {error && <div role="alert"><p>{error.message}</p>{error.retry && <button disabled={busy} onClick={()=>purchased(error.retry.itemId,error.retry.value)}>Retry purchased update</button>}</div>}
        {!lists ? <p role="status">Loading saved lists…</p> : lists.error ? <div role="alert">{lists.error}<button onClick={()=>setRevision(value=>value+1)}>Retry saved lists</button></div>
            : lists.data.length===0 ? <p>No saved shopping lists yet.</p>
            : <ul className="saved-list-picker">{lists.data.map(list=><li key={list.id}><button type="button" disabled={busy} aria-pressed={list.id===selected} onClick={()=>open(list.id)}>
                {list.start} to {list.end} · {list.items.length} items · {list.id.slice(0,8)}
            </button></li>)}</ul>}
        {selected && (!current ? <p role="status">Opening saved list…</p> : current.error ? <div role="alert">{current.error}<button onClick={()=>setRevision(value=>value+1)}>Retry opening saved list</button></div>
            : <div className="saved-list-details">
                <h3>Saved list: {saved.start} to {saved.end}</h3>
                {confirmDelete===key ? <div className="saved-list-delete-confirm" role="group" aria-label="Confirm saved list deletion">
                    <p>Delete this saved list permanently? Your recipes, scheduled meals, and other saved lists will stay.</p>
                    <button type="button" disabled={busy} onClick={remove}>{busy ? 'Deleting…' : 'Confirm delete'}</button>
                    <button type="button" disabled={busy} onClick={()=>{setConfirmDelete(null);setAction(null);}}>Cancel</button>
                </div> : <button className="saved-list-delete" type="button" disabled={busy} onClick={()=>{setConfirmDelete(key);setAction(null);setNotice('');}}>Delete list</button>}
                <p>{saved.items.filter(item=>item.purchased).length} of {saved.items.length} purchased</p>
                {saved.warnings.length>0 && <section aria-label="Saved list warnings"><h4>Unavailable recipes when saved</h4><ul>{saved.warnings.map((warning,index)=><li key={index}>{warning.message}</li>)}</ul></section>}
                {saved.items.length===0 ? <p>This saved list has no ingredients.</p> : <ul>{saved.items.map(item=><li key={item.id}>
                    <label className={item.purchased ? 'purchased-item' : ''}><input type="checkbox" checked={item.purchased} disabled={busy} onChange={event=>purchased(item.id,event.target.checked)} />{item.text}</label>
                    <span> · {item.occurrences} {item.occurrences===1 ? 'occurrence' : 'occurrences'}</span>
                </li>)}</ul>}
            </div>)}
    </section>;
}
