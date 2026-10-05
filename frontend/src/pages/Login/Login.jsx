import { useState } from "react";
import { Navigate } from "react-router-dom";
import { SessionStatus } from "../../auth/Auth";
import { useAuth } from "../../auth/AuthContext";
import Button from "../../components/Button/Button";
import "./Login.css";
import Input from "../../components/Input/Input";
import PannedOutLogo from "../../assets/logo/Panned_Out_Logo.PNG";

function Login() {
    const [message, setMessage] = useState("");
    const { user, loading, error, signIn } = useAuth();
    const [registering, setRegistering] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [busy, setBusy] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();
        setBusy(true);
        setMessage('');
        try { await signIn(registering ? 'register' : 'login', { email, password }); }
        catch (err) { setMessage(err.message); }
        finally { setBusy(false); }
    }

    if (loading || error) return <SessionStatus />;
    if (user) return <Navigate to="/calendar" replace />;
    return(
        <main className="login-page">

            <div className="brand-icon">
                        <img src={PannedOutLogo} alt="Brand Icon" />

                    </div>

            {/* Left Side of page */}
            <section className="login-brand">
                <div className="login-brand-content">

                    <h1>Panned Out</h1>

                    <p>
                        Plan your meals. 
                        <br />
                        Keep it simple.
                    </p>

                <div className="decorative-line"></div>

                <span>
                    Plan. Cook. Enjoy.
                </span>

                </div>
            </section>

            {/* Right Side of page */}
            <section className="login-section">

                <div className="login-card">

                    <div className="login-heading">
                        <span className="eyebrow">
                            PANNED OUT
                        </span>

                        <h2>{registering ? "Create your account" : "Welcome back!"}</h2>

                        <p>
                            {registering ? "Keep your recipes private in your own account." : "Sign in to continue your meal planning journey."}
                        </p>
                    </div>

                    <form onSubmit={handleSubmit}>

                        <Input
                        id="login-email"
                        name="email" required autoComplete="email" maxLength={254}
                        value={email} onChange={event => setEmail(event.target.value)}
                        label="Email address"
                        type="email"
                        placeholder="you@example.com"
                        />

                        <Input
                        id="login-password"
                        name="password" required minLength={registering ? 15 : 1} maxLength={128}
                        autoComplete={registering ? "new-password" : "current-password"}
                        value={password} onChange={event => setPassword(event.target.value)}
                        label="Password"
                        type="password"
                        placeholder="Enter your password"
                        />

                        {registering && <p>Use a password with 15 to 128 characters.</p>}

                        <Button type="submit" disabled={busy}>
                            {busy ? "Please wait..." : registering ? "Create account" : "Sign In"}
                        </Button>

                    </form>

                    {message && (
                        <p className="login-message" role="alert">
                            {message}
                        </p>
                    )}

                    <div className="signup-container">
                        <span>{registering ? "Already have an account?" : "New to Panned Out?"}</span>

                        <button
                            type="button"
                            className="signup-button" disabled={busy}
                            onClick={() => { setRegistering(value => !value); setMessage(""); setPassword(""); }}
                        >
                            {registering ? "Sign in" : "Create an account"}
                        </button>
                    </div>

                </div>

            </section>

        </main>
    );
}

export default Login;