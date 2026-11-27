export interface RouteLineProps {
  origin: string;
  destination: string;
  className?: string;
}

export function RouteLine({ origin, destination, className = "" }: RouteLineProps) {
  return (
    <div className={`route-line ${className}`.trim()} role="group" aria-label={`Rute: ${origin} ke ${destination}`}>
      <div className="route-endpoint">
        <span className="route-dot" aria-hidden="true" />
        <span className="route-label">{origin}</span>
      </div>
      <div className="route-connector" aria-hidden="true">
        <span className="route-dash" />
      </div>
      <div className="route-endpoint">
        <span className="route-dot route-dot-destination" aria-hidden="true" />
        <span className="route-label">{destination}</span>
      </div>
    </div>
  );
}
