import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { loginVk, pollDeviceLink } from "../shared/api.ts";
import { deviceLinkHints } from "../shared/music/services.ts";
import type { DeviceCode } from "../shared/music/types.ts";
import type { Service } from "../shared/types.ts";

type ServiceLinkProps = {
    service: Service
    deviceCode: DeviceCode | null
    onLinked: () => void
    onRestart: () => void
    onCancel: () => void
}

function getCodeHint(validationType?: string, phoneMask?: string) {
    if (validationType === "2fa_app") {
        return "Введите код из приложения для двухфакторной аутентификации.";
    }
    if (validationType === "2fa_callreset") {
        return "Вам позвонят — введите последние 4 цифры номера.";
    }
    return phoneMask ? "Введите код, который VK прислал на " + phoneMask + "." : "Введите код, который прислал VK.";
}

function ServiceLink({ service, deviceCode, onLinked, onRestart, onCancel }: ServiceLinkProps) {
    const [error, setError] = useState("");
    const [isFinished, setIsFinished] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const [login, setLogin] = useState("");
    const [password, setPassword] = useState("");
    const [code, setCode] = useState("");
    const [codeHint, setCodeHint] = useState("");
    const [isSending, setIsSending] = useState(false);

    useEffect(() => {
        if (!deviceCode || isFinished) {
            return;
        }

        const timer = setInterval(async () => {
            try {
                const result = await pollDeviceLink(service.id, deviceCode.device_code);
                if (result.status === "connected") {
                    setIsFinished(true);
                    onLinked();
                }
            } catch (err) {
                setIsFinished(true);
                setError(err instanceof Error ? err.message : "Не удалось проверить вход");
            }
        }, Math.max(deviceCode.interval, 2) * 1000);

        const timeout = setTimeout(() => {
            setIsFinished(true);
            setError("Время на вход истекло");
        }, deviceCode.expires_in * 1000);

        return () => {
            clearInterval(timer);
            clearTimeout(timeout);
        };
    }, [deviceCode, isFinished, onLinked, service.id]);

    async function copyCode() {
        if (!deviceCode) {
            return;
        }
        try {
            await navigator.clipboard.writeText(deviceCode.user_code);
            setIsCopied(true);
        } catch {
            setIsCopied(false);
        }
    }

    async function handleVkSubmit(event: FormEvent) {
        event.preventDefault();
        if (login.trim() === "" || password === "") {
            setError("Введите логин и пароль VK");
            return;
        }
        if (codeHint && code.trim() === "") {
            setError("Введите код");
            return;
        }
        setIsSending(true);
        setError("");
        try {
            const result = await loginVk(login, password, codeHint ? code : undefined);
            if (result.status === "connected") {
                setPassword("");
                onLinked();
            } else if (result.status === "need_code") {
                setCodeHint(getCodeHint(result.validation_type, result.phone_mask));
                if (result.invalid_code) {
                    setError("Неверный код — попробуйте ещё раз");
                }
            } else if (result.status === "need_captcha") {
                setError("VK просит пройти проверку «я не робот». Войдите в VK в браузере, а затем попробуйте привязать снова через несколько минут.");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось привязать аккаунт");
        }
        setIsSending(false);
    }

    return (
        <div className="source-form">
            <span className="label">ПРИВЯЗКА · {service.name.toUpperCase()}</span>

            {deviceCode && !isFinished && (
                <>
                    <p className="modal-text">{deviceLinkHints[service.id]}</p>
                    <div className="device-code">
                        <span className="device-code-value">{deviceCode.user_code}</span>
                        <button className="link-plain section-link" onClick={copyCode}>
                            {isCopied ? "СКОПИРОВАНО" : "СКОПИРОВАТЬ"}
                        </button>
                    </div>
                    <button
                        className="button accent auth-submit"
                        onClick={() => window.open(deviceCode.verification_url, "_blank", "noopener")}
                    >
                        Открыть страницу входа
                    </button>
                    <p className="search-note">Ждём подтверждения…</p>
                </>
            )}

            {!deviceCode && service.id === "vk" && (
                <form className="source-token" onSubmit={handleVkSubmit}>
                    <p className="modal-text">
                        Войдите своим аккаунтом VK. Пароль нужен только для входа — мы его не сохраняем.
                    </p>
                    <label className="auth-field">
                        <span className="label">ТЕЛЕФОН ИЛИ ПОЧТА</span>
                        <input
                            value={login}
                            autoComplete="username"
                            disabled={codeHint !== ""}
                            onChange={(event) => setLogin(event.target.value)}
                        />
                    </label>
                    <label className="auth-field">
                        <span className="label">ПАРОЛЬ</span>
                        <input
                            type="password"
                            value={password}
                            autoComplete="current-password"
                            disabled={codeHint !== ""}
                            onChange={(event) => setPassword(event.target.value)}
                        />
                    </label>
                    {codeHint && (
                        <label className="auth-field">
                            <span className="label">КОД ПОДТВЕРЖДЕНИЯ</span>
                            <span className="modal-text">{codeHint}</span>
                            <input
                                value={code}
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                onChange={(event) => setCode(event.target.value)}
                            />
                        </label>
                    )}
                    <button className="button accent auth-submit" type="submit" disabled={isSending}>
                        {isSending ? "Проверяем…" : codeHint ? "Подтвердить" : "Войти"}
                    </button>
                </form>
            )}

            {error && <p className="auth-error">{error}</p>}

            <div className="source-form-actions">
                {deviceCode && isFinished && error && (
                    <button className="button accent small" onClick={onRestart}>Попробовать снова</button>
                )}
                <button className="button outline-light small" onClick={onCancel}>Отмена</button>
            </div>
        </div>
    )
}

export default ServiceLink
