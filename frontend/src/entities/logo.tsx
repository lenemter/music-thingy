import logo from "../shared/images/logo.svg";
import logoDark from "../shared/images/logo-dark.svg";

type LogoProps = {
    dark?: boolean
}

function Logo({ dark = false }: LogoProps) {
    return (
        <a className={dark ? "logo dark" : "logo"} href="#">
            <img src={dark ? logoDark : logo} alt={"logo"} />
            <div>
                <h1>СИГНАЛ</h1>
                <p>вся музыка · один эфир</p>
            </div>
        </a>
    )
}

export default Logo
