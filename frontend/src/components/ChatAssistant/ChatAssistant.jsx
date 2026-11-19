import { useEffect, useRef, useState } from 'react';
import { chatRequest } from '../../api/chat';
import './ChatAssistant.css';

export default function ChatAssistant() {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [draft, setDraft] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [available, setAvailable] = useState(null);
    const active = useRef(null);
    const trigger = useRef(null);
    const input = useRef(null);
    const log = useRef(null);

    useEffect(() => () => active.current?.abort(), []);
    useEffect(() => {
        if (!open) return;
        const controller = new AbortController();
        chatRequest(undefined, [], controller.signal).then(result => setAvailable(result.available))
            .catch(err => { if (err.name !== 'AbortError') setError(err.message); });
        input.current?.focus();
        return () => controller.abort();
    }, [open]);
    useEffect(() => {
        if (log.current) log.current.scrollTop = log.current.scrollHeight;
    }, [messages, busy, open]);

    useEffect(() => {
        if (open && !busy) input.current?.focus();
    }, [open, busy]);

    function close() { setOpen(false); trigger.current?.focus(); }
    function clear() {
        active.current?.abort(); active.current = null;
        setMessages([]); setDraft(''); setError(''); setBusy(false);
        input.current?.focus();
    }
    async function send(event) {
        event.preventDefault();
        const text = draft.trim();
        if (!text || busy || available !== true) return;
        const controller = new AbortController();
        active.current = controller;
        // Only completed pairs enter context; bound history by turns and size.
        let history = messages.slice(-10);
        while (history.reduce((sum, item) => sum + item.text.length, text.length) > 16000) history = history.slice(2);
        setMessages(current => [...current, { role: 'user', text }]);
        setDraft(''); setBusy(true); setError('');
        const timeout = setTimeout(() => controller.abort(), 30000);
        try {
            const result = await chatRequest(text, history, controller.signal);
            if (active.current !== controller) return;
            setMessages(current => [...current, { role: 'model', text: result.reply }]);
        } catch (err) {
            if (active.current !== controller) return;
            setMessages(current => current.slice(0, -1));
            setDraft(text);
            setError(err.name === 'AbortError' ? 'The request timed out. Please try again.' : err.message);
        } finally {
            clearTimeout(timeout);
            if (active.current === controller) { active.current = null; setBusy(false); }
        }
    }

    return <div className="chat-assistant">
        <button ref={trigger} className="chat-launcher" aria-expanded={open} aria-controls="kitchen-chat" onClick={() => setOpen(value => !value)}>✳ Kitchen assistant</button>
        {open && <section id="kitchen-chat" className="chat-panel" aria-labelledby="chat-title" onKeyDown={event => {
            if (event.key === 'Escape') { event.stopPropagation(); close(); }
        }}>
            <header className="chat-header"><div><span>PANNED OUT · KITCHEN ASSISTANT</span><h2 id="chat-title">A little kitchen help</h2></div><button onClick={close} aria-label="Close kitchen assistant">×</button></header>
            <p className="chat-disclosure">Messages and recent chat history are sent to GroqCloud. Replies may be inaccurate. Saved recipes aren’t shared automatically.</p>
            <div ref={log} className="chat-messages" role="log" aria-label="Conversation" aria-live="polite">
                {!messages.length && <div className="chat-welcome"><h3>What’s cooking?</h3><p>Ask for meal ideas, ingredient swaps, or help finding your way around Panned Out.</p>
                    {['What can I cook with rice and beans?', 'How do I plan a meal?', 'What can I use instead of butter?'].map(question => <button key={question} disabled={busy} onClick={() => { setDraft(question); input.current?.focus(); }}>{question}</button>)}
                </div>}
                {messages.map((message, index) => <div className={`chat-message chat-${message.role}`} key={index}><strong>{message.role === 'user' ? 'You' : 'Kitchen assistant'}</strong><p>{message.text}</p></div>)}
                {busy && <p role="status">Thinking…</p>}
            </div>
            {available === false && <p className="chat-notice" role="status">The AI assistant hasn’t been connected yet. It will be ready once the app administrator completes setup.</p>}
            {error && <p className="chat-notice" role="alert">{error}</p>}
            <form onSubmit={send} className="chat-form">
                <label htmlFor="chat-message">Your message</label>
                <textarea ref={input} id="chat-message" rows={2} maxLength={2000} value={draft} disabled={busy} onChange={event => setDraft(event.target.value)} placeholder="Ask about meals or the app…" />
                <div><button type="button" onClick={clear}>New chat</button><button className="chat-send" type="submit" disabled={busy || available !== true || !draft.trim()}>{busy ? 'Sending…' : 'Send'}</button></div>
            </form>
        </section>}
    </div>;
}
