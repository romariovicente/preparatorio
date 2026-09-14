import React, { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Vector3 } from 'three';

export default function PlayerController({ position, setPosition, cameraMode, touchInput }) {
  const { camera } = useThree();
  const keys = useRef({ forward: false, backward: false, left: false, right: false });
  const velocity = useRef(new Vector3(0, 0, 0));

  useEffect(() => {
    const handleKeyDown = (e) => {
      switch (e.key.toLowerCase()) {
        case 'w': case 'arrowup': keys.current.forward = true; break;
        case 's': case 'arrowdown': keys.current.backward = true; break;
        case 'a': case 'arrowleft': keys.current.left = true; break;
        case 'd': case 'arrowright': keys.current.right = true; break;
        default: break;
      }
    };

    const handleKeyUp = (e) => {
      switch (e.key.toLowerCase()) {
        case 'w': case 'arrowup': keys.current.forward = false; break;
        case 's': case 'arrowdown': keys.current.backward = false; break;
        case 'a': case 'arrowleft': keys.current.left = false; break;
        case 'd': case 'arrowright': keys.current.right = false; break;
        default: break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  useFrame((state, delta) => {
    const speed = 5 * delta;
    const dir = new Vector3();

    const moveFwd = keys.current.forward || (touchInput?.y > 0);
    const moveBwd = keys.current.backward || (touchInput?.y < 0);
    const moveLeft = keys.current.left || (touchInput?.x < 0);
    const moveRight = keys.current.right || (touchInput?.x > 0);

    if (moveFwd) dir.z -= 1;
    if (moveBwd) dir.z += 1;
    if (moveLeft) dir.x -= 1;
    if (moveRight) dir.x += 1;

    dir.normalize();

    const newX = position[0] + dir.x * speed;
    const newZ = position[2] + dir.z * speed;
    setPosition([newX, position[1], newZ]);

    if (cameraMode === 'third') {
      camera.position.set(newX, position[1] + 2.5, newZ + 4.5);
      camera.lookAt(newX, position[1] + 1, newZ);
    } else {
      camera.position.set(newX, position[1] + 1.6, newZ);
      camera.lookAt(newX + dir.x, position[1] + 1.6, newZ + dir.z - 1);
    }
  });

  return null;
}
