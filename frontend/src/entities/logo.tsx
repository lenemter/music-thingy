import logo from "../shared/images/logo.svg";

function Logo() {
    return (
        <a className="logo" href="#">
            <img src={logo} alt={"logo"} />
            <div>
                <h1>СИГНАЛ</h1>
                <p>вся музыка · один эфир</p>
            </div>
        </a>
    )
}

export default Logo
