import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Device from "./pages/Device";
import Profile from "./pages/Profile";
import World from "./game/world/World";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/device" element={<Device />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/game" element={<World />} />
                <Route path="/world" element={<World />} />
            </Routes>
        </BrowserRouter>
    );
}
