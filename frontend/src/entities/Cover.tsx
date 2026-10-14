import Grain from "./Grain.tsx";

type CoverProps = {
    src: string
    size: "small" | "row" | "card"
}

function Cover({ src, size }: CoverProps) {
    return (
        <span className={"cover " + size}>
            <img src={src} alt=""/>
            <Grain/>
        </span>
    )
}

export default Cover
