import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Register() {

    const navigate = useNavigate();

    const [form, setForm] = useState({
        name: "",
        email: "",
        password: "",
        profession: ""
    });

    function updateField(event) {
        setForm({
            ...form,
            [event.target.name]: event.target.value
        });
    }

    function handleRegister(event) {
        event.preventDefault();

        const player = {
            name: form.name,
            email: form.email,
            profession: form.profession,
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
                    NOVO JOGADOR
                </span>

                <h1>Criar conta</h1>

                <form onSubmit={handleRegister}>

                    <label>Nome</label>

                    <input
                        name="name"
                        value={form.name}
                        onChange={updateField}
                        placeholder="Nome do jogador"
                        required
                    />

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
                        placeholder="Crie sua senha"
                        required
                    />

                    <label>Profissão / área inicial</label>

                    <select
                        name="profession"
                        value={form.profession}
                        onChange={updateField}
                        required
                    >
                        <option value="">
                            Selecione
                        </option>

                        <option>
                            Auxiliar de Enfermagem
                        </option>

                        <option>
                            Técnico de Enfermagem
                        </option>

                        <option>
                            Enfermeiro(a)
                        </option>

                        <option>
                            Medicina
                        </option>

                        <option>
                            Farmácia
                        </option>

                        <option>
                            Pesquisa
                        </option>

                        <option>
                            Computação
                        </option>

                        <option>
                            Engenharia
                        </option>

                        <option>
                            Transporte
                        </option>
                    </select>

                    <button className="button primary" type="submit">
                        Criar conta
                    </button>

                </form>

                <Link to="/">
                    Voltar
                </Link>

            </section>

        </main>
    );
}
