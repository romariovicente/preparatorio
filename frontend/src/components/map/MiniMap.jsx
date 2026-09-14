import { WORLD_LOCATIONS } from "../../game/world/locations/worldLocations";

export default function MiniMap() {
    return (
        <div className="mini-map">
            <div className="mini-map-title">
                MAPA
            </div>

            <div className="mini-map-grid">
                {WORLD_LOCATIONS.map((location) => (
                    <span
                        key={location.id}
                        className={`map-point ${location.category}`}
                        title={location.name}
                    >
                        •
                    </span>
                ))}

                <span className="player-point">
                    ●
                </span>
            </div>
        </div>
    );
}
