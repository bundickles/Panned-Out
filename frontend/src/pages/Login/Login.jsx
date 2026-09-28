import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../../components/Button/Button";
import "./Login.css";
import Input from "../../components/Input/Input";
import PannedOutLogo from "../../assets/logo/Panned_Out_Logo.PNG";

function Login() {
    const [message, setMessage] = useState("");
    const navigate = useNavigate();

    function handleSubmit(event) {
        event.preventDefault();
        
        // Placeholder for backend login integration, takeout once connected
        navigate("/calendar");
        
    }

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

                        <h2>Welcome back!</h2>

                        <p>
                            Please sign in to continue your
                            meal planning journey.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit}>

                        <Input
                        label="Email address"
                        type="email"
                        placeholder="you@example.com"
                        />

                        <Input
                        label="Password"
                        type="password"
                        placeholder="Enter your password"
                        />

                        <div className="forgot-password-container">
                            <button
                                type="button"
                                className="forgot-password-button"
                            >
                                Forgot Password?
                            </button>
                        </div>

                        <Button type="submit">
                            Sign In
                        </Button>

                    </form>

                    {message && (
                        <p className="login-message">
                            {message}
                        </p>
                    )}

                    <div className="signup-container">
                        <span>New to Panned Out?</span>

                        <button
                            type="button"
                            className="signup-button"
                        >
                            Create an account
                        </button>
                    </div>

                </div>

            </section>

        </main>
    );
}

export default Login;