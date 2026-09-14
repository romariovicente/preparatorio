import { useState } from "react";

export default function MobileControls() {
    const [active, setActive] = useState(false);

    function send(action) {
        window.dispatchEvent(
            new CustomEvent(
                "preparatorio-input",
                {
                    detail: action
                }
            )
        );
    }

    return (
        <div className="mobile-controls">
            <div
                className="joystick"
                onPointerDown={() => setActive(true)}
                onPointerUp={() => setActive(false)}
            >
                <div className={active ? "stick active" : "stick"} />
            </div>

            <div className="mobile-actions">
                <button onClick={() => send("interact")}>
                    E
                </button>

                <button onClick={() => send("camera")}>
                    V
                </button>

                <button onClick={() => send("map")}>
                    M
                </button>
            </div>
        </div>
    );
}
