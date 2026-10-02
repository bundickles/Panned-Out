import "./Input.css";

function Input({ label, type = "text", placeholder, id, ...props }) {
    return (
        <div className="input-group">
            <label htmlFor={id}>{label}</label>
            
            <input id={id} type={type} placeholder={placeholder} {...props} />
        </div>
    );
}

export default Input;