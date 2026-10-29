import { useState } from "react";
import type { FormEvent } from "react";
import Logo from "../entities/logo.tsx";
import Grain from "../entities/Grain.tsx";
import type { User } from "../shared/types.ts";
import { login, register } from "../shared/api.ts";
import ArrowIcon from "../shared/icons/arrow-right.svg?react";

type AuthPageProps = {
    onLogin: (user: User) => void
}

function AuthPage({ onLogin }: AuthPageProps) {
    const [mode, setMode] = useState<"login" | "register">("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordRepeat, setPasswordRepeat] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const isLogin = mode === "login";
    const passwordsDiffer = passwordRepeat !== "" && passwordRepeat !== password;

    function changeMode(newMode: "login" | "register") {
        setMode(newMode);
        setError("");
    }

    async function handleSubmit(event: FormEvent) {
        event.preventDefault();

        if (!isLogin && name.trim() === "") {
            setError("Введите имя");
            return;
        }
        if (!email.includes("@")) {
            setError("Введите корректную почту");
            return;
        }
        if (password === "") {
            setError("Введите пароль");
            return;
        }
        if (!isLogin && password.length < 8) {
            setError("Пароль должен быть не короче 8 символов");
            return;
        }
        if (!isLogin && passwordRepeat !== password) {
            setError("Пароли не совпадают");
            return;
        }

        setError("");
        setIsLoading(true);

        try {
            let user: User;
            if (isLogin) {
                user = await login(email.trim(), password);
            } else {
                user = await register(email.trim(), name.trim(), password);
            }
            onLogin(user);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Что-то пошло не так");
            setIsLoading(false);
        }
    }

    return (
        <div className="auth">
            <aside className="auth-aside">
                <Grain/>
                <Logo dark/>

                <div className="auth-promo">
                    <h1>Яндекс, Spotify и SoundCloud в одном эфире</h1>
                    <p>Один аккаунт, чтобы искать, слушать, собирать плейлисты и править треки из всех сервисов.</p>
                    <div className="auth-stamp">
                        <span className="auth-barcode"/>
                        <span>SGNL · ВХОД · 2026</span>
                    </div>
                </div>
            </aside>

            <main className="auth-main">
                <div className="auth-box">
                    <div className="auth-tabs">
                        <button
                            className={isLogin ? "auth-tab active" : "auth-tab"}
                            onClick={() => changeMode("login")}
                        >
                            Войти
                        </button>
                        <button
                            className={isLogin ? "auth-tab" : "auth-tab active"}
                            onClick={() => changeMode("register")}
                        >
                            Создать аккаунт
                        </button>
                    </div>

                    <form className="auth-form" onSubmit={handleSubmit} noValidate>
                        <div className="auth-heading">
                            <h2>{isLogin ? "С возвращением" : "Новый аккаунт"}</h2>
                            <p>
                                {isLogin
                                    ? "Ваши плейлисты и правки треков ждут в эфире."
                                    : "Подключите сервисы после регистрации — вся музыка соберётся в одном месте."}
                            </p>
                        </div>

                        {!isLogin && (
                            <label className="auth-field">
                                <span className="label">ИМЯ</span>
                                <input
                                    type="text"
                                    placeholder="Как к вам обращаться"
                                    value={name}
                                    onChange={(event) => setName(event.target.value)}
                                />
                            </label>
                        )}

                        <label className="auth-field">
                            <span className="label">ПОЧТА</span>
                            <input
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                            />
                        </label>

                        <label className="auth-field">
                            <span className="label auth-field-top">
                                ПАРОЛЬ
                            </span>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                            />
                        </label>

                        {!isLogin && (
                            <label className="auth-field">
                                <span className="label">ПОВТОРИТЕ ПАРОЛЬ</span>
                                <input
                                    className={passwordsDiffer ? "invalid" : ""}
                                    type="password"
                                    placeholder="••••••••"
                                    value={passwordRepeat}
                                    onChange={(event) => setPasswordRepeat(event.target.value)}
                                />
                            </label>
                        )}

                        {error && <p className="auth-error">{error}</p>}

                        <button className="button accent auth-submit" type="submit" disabled={isLoading}>
                            {isLoading ? "Подождите…" : isLogin ? "Войти" : "Создать аккаунт"}
                            <ArrowIcon/>
                        </button>
                    </form>
                </div>
            </main>
        </div>
    )
}

export default AuthPage
