import { useEffect, useRef } from "react";
import { Vector3 } from "three";

export function useCameraMode() {
    const modeRef = useRef(
        localStorage.getItem("preparatorio_camera") || "third-person"
    );

    useEffect(() => {
        function switchCamera() {
            modeRef.current =
                modeRef.current === "third-person"
                    ? "first-person"
                    : "third-person";

            localStorage.setItem(
                "preparatorio_camera",
                modeRef.current
            );

            window.dispatchEvent(
                new CustomEvent(
                    "preparatorio-camera-change",
                    {
                        detail: modeRef.current
                    }
                )
            );
        }

        window.addEventListener(
            "preparatorio-toggle-camera",
            switchCamera
        );

        return () => {
            window.removeEventListener(
                "preparatorio-toggle-camera",
                switchCamera
            );
        };
    }, []);

    return modeRef;
}

export function getFollowPosition(playerPosition, mode) {
    const position = new Vector3(...playerPosition);

    if (mode === "first-person") {
        return position.add(
            new Vector3(0, 1.55, 0)
        );
    }

    return position.add(
        new Vector3(0, 3, 7)
    );
}
