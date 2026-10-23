import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { authRequest } from '../api/auth';
import './Auth.css';

import { AuthContext, useAuth } from "./AuthContext";
const CHANGE_KEY = 'panned-out-account-change';

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [revision, setRevision] = useState(0);

    useEffect(() => {
        let active = true;
        authRequest('me').then(value => {
            if (active) { setUser(value); setError(''); }
        }).catch(err => {
            if (active) setError(err.message);
        }).finally(() => {
            if (active) setLoading(false);
        });
        return () => { active = false; };
    }, [revision]);

    useEffect(() => {
        const expired = () => { setUser(null); setError(''); };
        const changed = event => {
            if (event.key === CHANGE_KEY) {
                setUser(null);
                setLoading(true);
                setRevision(value => value + 1);
            }
        };
        window.addEventListener('panned-session-expired', expired);
        window.addEventListener('storage', changed);
        return () => {
            window.removeEventListener('panned-session-expired', expired);
            window.removeEventListener('storage', changed);
        };
    }, []);

    function notifyOtherTabs() {
        // This contains no session token or account data; cookies remain HttpOnly.
        try { localStorage.setItem(CHANGE_KEY, crypto.randomUUID()); } catch { /* Storage may be disabled. */ }
    }

    async function signIn(mode, fields) {
        const account = await authRequest(mode, fields);
        setUser(account);
        setError('');
        notifyOtherTabs();
    }

    async function signOut() {
        await authRequest('logout', {});
        setUser(null);
        setError('');
        notifyOtherTabs();
    }

    return <AuthContext.Provider value={{ user, loading, error, signIn, signOut,
        retry: () => { setUser(null); setLoading(true); setRevision(value => value + 1); } }}>{children}</AuthContext.Provider>;
}



export function SessionStatus() {
    const { loading, error, retry } = useAuth();
    if (loading) return <p role="status">Checking your session...</p>;
    if (error) return <div role="alert"><p>{error}</p><button onClick={retry}>Retry connection</button></div>;
    return null;
}

export function PrivatePages() {
    const { user, loading, error, signOut } = useAuth();
    const [logoutError, setLogoutError] = useState('');
    const [busy, setBusy] = useState(false);
    if (loading || error) return <SessionStatus />;
    if (!user) return <Navigate to="/login" replace />;
    return <div key={user.id}>
        <div className="account-bar">
            <span>Signed in as {user.email}</span>
            <button disabled={busy} onClick={async () => {
                setBusy(true);
                setLogoutError('');
                try { await signOut(); }
                catch (err) { setLogoutError(err.message); }
                finally { setBusy(false); }
            }}>{busy ? 'Signing out...' : 'Log out'}</button>
            {logoutError && <span role="alert">{logoutError}</span>}
        </div>
        <Outlet />
    </div>;
}
