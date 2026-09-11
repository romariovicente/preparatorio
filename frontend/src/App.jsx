import "./App.css";

function App() {
    return (
        <main className="app">
            <div className="hud-grid"></div>

            <section className="hero">

                <div className="brand">
                    <span className="brand-icon">✚</span>

                    <div>
                        <h1>PREPARATÓRIO</h1>
                        <p>DO TÉCNICO DE ENFERMAGEM À MEDICINA</p>
                    </div>
                </div>

                <div className="creator">
                    Criado por <strong>Romario Vicente Amaro</strong>
                </div>

                <div className="hero-description">
                    <p>
                        Um mundo virtual brasileiro de educação,
                        saúde, ciência, profissões, exploração
                        e multiplayer.
                    </p>
                </div>

                <div className="hero-actions">
                    <button className="primary-button">
                        ENTRAR NO JOGO
                    </button>

                    <button className="secondary-button">
                        CRIAR CONTA
                    </button>

                    <button className="secondary-button">
                        ENTRAR
                    </button>
                </div>

                <div className="systems">
                    <div>🏥 HOSPITAL</div>
                    <div>🎓 UNIVERSIDADE</div>
                    <div>🚑 EMERGÊNCIA</div>
                    <div>🔬 PESQUISA</div>
                    <div>🚗 MUNDO ABERTO</div>
                    <div>👥 MULTIPLAYER</div>
                </div>

                <div className="camera-info">
                    <span>TERCEIRA PESSOA — PADRÃO</span>
                    <span>PRIMEIRA PESSOA — OPCIONAL</span>
                </div>

            </section>
        </main>
    );
}

export default App;
