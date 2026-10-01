import "./Button.css";

function Button({ children, type = "button", onClick }) {
    return (
        <button type={type} onClick={onClick} className="primary-button">
            {children}
        </button>
    );
}

export default Button;