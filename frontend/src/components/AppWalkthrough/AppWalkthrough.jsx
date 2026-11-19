import { useEffect, useRef, useState } from 'react';
import './AppWalkthrough.css';

const steps = [
    {
        title: 'Welcome to Panned Out',
        icon: '✳',
        description: 'A little planning makes room for good food. Take a quick look around your kitchen companion.',
        tip: 'Save recipes, plan meals, and keep your shopping organized.',
    },
    {
        title: 'Keep your favorite recipes',
        icon: '🍽',
        description: 'Open Recipes to add a recipe with ingredients and instructions. Search your collection by name or filter by category.',
        tip: 'Open a recipe card to read the full recipe and check off ingredients as you prepare.',
    },
    {
        title: 'Make room for meals',
        icon: '▦',
        description: 'Use Calendar to choose a day and add a meal. Switch between month, week, and day views to see what’s coming up.',
        tip: 'Start with one meal on one day. You can build the rest of your plan later.',
    },
    {
        title: 'Bring your shopping together',
        icon: '🛒',
        description: 'Open Shopping List to see ingredients from your scheduled meals. Choose a date range and generate your list.',
        tip: 'Update meals in Calendar, then generate again to refresh the ingredients you need.',
    },
    {
        title: 'Find your next meal idea',
        icon: '📖',
        description: 'Explore Meal Plans for dietary collections, or create a custom plan to organize your own meal ideas.',
        tip: 'You’re ready to explore. Reopen this walkthrough anytime using App tour at the top of the page.',
    },
];

export default function AppWalkthrough({ userId }) {
    const storageKey = `panned-out:walkthrough:v1:${userId}`;
    const dialog = useRef(null);
    const trigger = useRef(null);
    const heading = useRef(null);
    const [step, setStep] = useState(0);

    useEffect(() => {
        let dismissed = false;
        try { dismissed = localStorage.getItem(storageKey) === 'dismissed'; }
        catch { /* The tour also works when browser storage is unavailable. */ }
        const element = dialog.current;
        if (!dismissed) element.showModal();
        return () => element.close();
    }, [storageKey]);

    useEffect(() => {
        if (dialog.current.open) heading.current.focus();
    }, [step]);

    function dismiss() {
        try { localStorage.setItem(storageKey, 'dismissed'); }
        catch { /* Dismiss for this session even if the preference cannot be saved. */ }
        dialog.current.close();
    }

    function keepFocusInTour(event) {
        if (event.key !== 'Tab') return;
        const buttons = [...dialog.current.querySelectorAll('button:not(:disabled)')];
        const first = buttons[0];
        const last = buttons[buttons.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === heading.current)) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    const current = steps[step];
    return (
        <>
            <button type="button" ref={trigger} onClick={() => {
                setStep(0);
                dialog.current.showModal();
                heading.current.focus();
            }}>App tour</button>
            <dialog ref={dialog} className="app-walkthrough" aria-labelledby="walkthrough-title"
                aria-describedby="walkthrough-description" onKeyDown={keepFocusInTour}
                onCancel={event => { event.preventDefault(); dismiss(); }}
                onClose={() => trigger.current?.focus()}>
                <div className="walkthrough-topline">
                    <span>PANNED OUT · QUICK TOUR</span>
                    <button type="button" onClick={dismiss}>Skip tour</button>
                </div>
                <div className="walkthrough-icon" aria-hidden="true">{current.icon}</div>
                <p className="walkthrough-progress">Step {step + 1} of {steps.length}</p>
                <h2 id="walkthrough-title" ref={heading} tabIndex={-1}>{current.title}</h2>
                <p id="walkthrough-description" className="walkthrough-description">{current.description}</p>
                <p className="walkthrough-tip">{current.tip}</p>
                <div className="walkthrough-dots" aria-hidden="true">
                    {steps.map((item, index) => <span key={item.title} className={index === step ? 'active' : ''} />)}
                </div>
                <div className="walkthrough-actions">
                    <button type="button" disabled={step === 0} onClick={() => setStep(value => value - 1)}>Back</button>
                    {step === steps.length - 1
                        ? <button type="button" className="walkthrough-primary" onClick={dismiss}>Finish tour</button>
                        : <button type="button" className="walkthrough-primary" onClick={() => setStep(value => value + 1)}>{step === 0 ? 'Show me around' : 'Next'}</button>}
                </div>
            </dialog>
        </>
    );
}
