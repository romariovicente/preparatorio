import { useNavigate } from "react-router-dom";

export default function Profile() {
    const navigate = useNavigate();

    const player = JSON.parse(
        localStorage.getItem("preparatorio_player") || "{}"
    );

    const device =
        localStorage.getItem("preparatorio_device") || "desktop";

    function enterGame() {
        navigate("/game");
    }

    return (
        <main className="page">
            <section className="profile-card">
                <span className="eyebrow">
                    PERFIL DO JOGADOR
                </span>

                <h1>
                    {player.name || "Jogador"}
                </h1>

                <div className="profile-data">
                    <p>
                        <strong>Profissão:</strong>{" "}
                        {player.profession || "Não definida"}
                    </p>

                    <p>
                        <strong>Dispositivo:</strong>{" "}
                        {device === "mobile"
                            ? "Celular"
                            : "Computador"}
                    </p>

                    <p>
                        <strong>Nível:</strong> 1
                    </p>

                    <p>
                        <strong>XP:</strong> 0
                    </p>
                </div>

                <button
                    className="button primary"
                    onClick={enterGame}
                >
                    Entrar no mundo
                </button>
            </section>
        </main>
    );
}
