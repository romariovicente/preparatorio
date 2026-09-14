import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Login() {
    const navigate = useNavigate();
    const [form, setForm] = useState({
        email: "",
        password: ""
    });

    function updateField(event) {
        setForm({
            ...form,
            [event.target.name]: event.target.value
        });
    }

    function handleLogin(event) {
        event.preventDefault();
        const player = {
            name: form.email.split("@")[0] || "Jogador",
            email: form.email,
            profession: "Não informada",
            loggedIn: true
        };
        localStorage.setItem(
            "preparatorio_player",
            JSON.stringify(player)
        );
        navigate("/device");
    }

    return (
        <main className="page">
            <section className="form-card">
                <span className="eyebrow">
                    ACESSAR CONTA
                </span>
                <h1>Entrar no Jogo</h1>
                <form onSubmit={handleLogin}>
                    <label>E-mail</label>
                    <input
                        type="email"
                        name="email"
                        value={form.email}
                        onChange={updateField}
                        placeholder="seu@email.com"
                        required
                    />
                    <label>Senha</label>
                    <input
                        type="password"
                        name="password"
                        value={form.password}
                        onChange={updateField}
                        placeholder="Sua senha"
                        required
                    />
                    <button className="button primary" type="submit">
                        Entrar
                    </button>
                </form>
                <Link to="/">
                    Voltar para o início
                </Link>
            </section>
        </main>
    );
}
