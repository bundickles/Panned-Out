import { useEffect, useRef, useState } from 'react';
import './RecipeCooking.css';

export default function RecipeCooking({ instructions, name }) {
    const dialog = useRef(null);
    const [step, setStep] = useState(0);
    const [minutes, setMinutes] = useState('5');
    const [remaining, setRemaining] = useState(0);
    const [deadline, setDeadline] = useState(null);
    const [finished, setFinished] = useState(false);
    const [error, setError] = useState('');
    const trigger = useRef(null);

    useEffect(() => {
        if (deadline === null) return;
        function tick() {
            const left = Math.max(0, deadline - Date.now());
            setRemaining(left);
            if (left === 0) {
                setDeadline(null);
                setFinished(true);
            }
        }
        tick();
        const interval = setInterval(tick, 200);
        return () => clearInterval(interval);
    }, [deadline]);

    function start() {
        const duration = Number(minutes);
        if (!Number.isFinite(duration) || duration <= 0 || duration > 1440) {
            setError('Enter a duration greater than 0 and up to 1440 minutes.');
            return;
        }
        const ms = Math.round(duration * 60000);
        if (ms < 1000) {
            setError('Choose a duration of at least one second.');
            return;
        }
        setError('');
        setFinished(false);
        setRemaining(ms);
        setDeadline(Date.now() + ms);
    }

    function pause() {
        const left = Math.max(0, deadline - Date.now());
        setRemaining(left);
        setDeadline(null);
        setFinished(left === 0);
    }

    function reset() {
        setDeadline(null);
        setRemaining(0);
        setFinished(false);
        setError('');
    }

    const seconds = Math.ceil(remaining / 1000);
    const display = `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
    const status = finished ? 'Time’s up! Check your food.' : deadline !== null ? 'Timer running' : remaining > 0 ? 'Timer paused' : 'Set a cooking timer';

    return (
        <div className="recipe-cooking">
            <button ref={trigger} className="journal-secondary-button" onClick={() => dialog.current.showModal()}>
                Open cooking focus view
            </button>
            {(remaining > 0 || finished) && <p role="status">{status} {remaining > 0 && display}</p>}
            <dialog ref={dialog} className="cooking-dialog" aria-labelledby="cooking-title"
                onClose={() => trigger.current?.focus()}>
                <header className="cooking-header">
                    <div><p>COOKING FOCUS</p><h2 id="cooking-title">{name}</h2></div>
                    <button autoFocus className="journal-secondary-button" onClick={() => dialog.current.close()}>Close focus view</button>
                </header>
                <section aria-label="Recipe instructions" className="cooking-step">
                    <div aria-live="polite" aria-atomic="true">
                        <p>Step {step + 1} of {instructions.length}</p>
                        <p className="cooking-instruction">{instructions[step]}</p>
                    </div>
                    <nav aria-label="Instruction steps" className="cooking-controls">
                        <button className="journal-secondary-button" disabled={step === 0} onClick={() => setStep(step - 1)}>Previous step</button>
                        <button className="journal-primary-button" disabled={step === instructions.length - 1} onClick={() => setStep(step + 1)}>Next step</button>
                    </nav>
                    {step === instructions.length - 1 && <p>Last step — enjoy your meal when it’s ready.</p>}
                </section>
                <section className="cooking-timer" aria-labelledby="timer-title">
                    <h3 id="timer-title">Cooking timer</h3>
                    <p role="timer" aria-label="Time remaining" className="cooking-clock">{display}</p>
                    <p role="status">{status}</p>
                    <label htmlFor="cooking-minutes">Duration (minutes)</label>
                    <input id="cooking-minutes" type="number" min="0.017" max="1440" step="any"
                        value={minutes} disabled={remaining > 0} onChange={event => setMinutes(event.target.value)} aria-describedby={error ? 'timer-error' : undefined} aria-invalid={!!error} />
                    {error && <p id="timer-error" role="alert">{error}</p>}
                    <div className="cooking-controls">
                        {deadline !== null ? <button className="journal-primary-button" onClick={pause}>Pause timer</button>
                            : remaining > 0 ? <button className="journal-primary-button" onClick={() => setDeadline(Date.now() + remaining)}>Resume timer</button>
                                : <button className="journal-primary-button" onClick={start}>Start timer</button>}
                        <button className="journal-secondary-button" onClick={reset}>Reset timer</button>
                    </div>
                    <p className="cooking-note">The timer keeps running when you close this view. Leaving or refreshing the recipe clears it.</p>
                </section>
            </dialog>
        </div>
    );
}
