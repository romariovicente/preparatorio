import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Vector3 } from "three";

export default function PlayerController({ setPosition }) {
    const keys = useRef({ forward: false, backward: false, left: false, right: false, jump: false, run: false });

    useEffect(() => {
        function handleKeyDown(e) {
            if (e.key === "w" || e.key === "W" || e.key === "ArrowUp") keys.current.forward = true;
            if (e.key === "s" || e.key === "S" || e.key === "ArrowDown") keys.current.backward = true;
            if (e.key === "a" || e.key === "A" || e.key === "ArrowLeft") keys.current.left = true;
            if (e.key === "d" || e.key === "D" || e.key === "ArrowRight") keys.current.right = true;
            if (e.key === " ") keys.current.jump = true;
            if (e.key === "Shift") keys.current.run = true;
        }

        function handleKeyUp(e) {
            if (e.key === "w" || e.key === "W" || e.key === "ArrowUp") keys.current.forward = false;
            if (e.key === "s" || e.key === "S" || e.key === "ArrowDown") keys.current.backward = false;
            if (e.key === "a" || e.key === "A" || e.key === "ArrowLeft") keys.current.left = false;
            if (e.key === "d" || e.key === "D" || e.key === "ArrowRight") keys.current.right = false;
            if (e.key === " ") keys.current.jump = false;
            if (e.key === "Shift") keys.current.run = false;
        }

        window.addEventListener("keydown", handleKeyDown);
        window.addEventListener("keyup", handleKeyUp);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            window.removeEventListener("keyup", handleKeyUp);
        };
    }, []);

    useFrame((state, delta) => {
        const speed = keys.current.run ? 8 : 4;
        const moveVector = new Vector3(0, 0, 0);

        if (keys.current.forward) moveVector.z -= 1;
        if (keys.current.backward) moveVector.z += 1;
        if (keys.current.left) moveVector.x -= 1;
        if (keys.current.right) moveVector.x += 1;

        moveVector.normalize();
        moveVector.multiplyScalar(speed * delta);

        setPosition((prev) => [
            prev[0] + moveVector.x,
            prev[1],
            prev[2] + moveVector.z
        ]);
    });

    return null;
}
