import { useNavigate } from "react-router-dom";

export default function Device() {
    const navigate = useNavigate();

    function chooseDevice(device) {
        localStorage.setItem("preparatorio_device", device);
        navigate("/profile");
    }

    return (
        <main className="page">
            <section className="form-card">
                <span className="eyebrow">CONFIGURAÇÃO DO JOGADOR</span>
                <h1>Como você está jogando?</h1>
                <p>Escolha o dispositivo para carregar a interface adequada.</p>
                <button className="button primary" onClick={() => chooseDevice("mobile")}>
                    📱 Estou jogando no telefone
                </button>
                <button className="button secondary" onClick={() => chooseDevice("desktop")}>
                    🖥️ Estou jogando no computador
                </button>
            </section>
        </main>
    );
}