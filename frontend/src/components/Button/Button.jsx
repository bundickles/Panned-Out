import "./Button.css";

function Button({ children, type = "button", onClick, disabled }) {
    return (
        <button type={type} onClick={onClick} disabled={disabled} className="primary-button">
            {children}
        </button>
    );
}

export default Button;