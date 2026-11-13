
import { useEffect, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";

type GPSPoint = {
  latitude: number | null;
  longitude: number | null;
};

type Props = {
  records: GPSPoint[];
};

function FitBounds({
  positions,
}: {
  positions: [number, number][];
}) {
  const map = useMap();

  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(positions as LatLngBoundsExpression, {
        padding: [30, 30],
      });
    }
  }, [map, positions]);

  return null;
}

export default function RouteMap({ records }: Props) {
  const positions = useMemo<[number, number][]>(
    () =>
      records
        .filter(
          (r) =>
            r.latitude != null &&
            r.longitude != null &&
            Number.isFinite(r.latitude) &&
            Number.isFinite(r.longitude) &&
            Math.abs(r.latitude) <= 90 &&
            Math.abs(r.longitude) <= 180
        )
        .map((r) => [
          r.latitude as number,
          r.longitude as number,
        ]),
    [records]
  );

  if (positions.length < 2) {
    return <p>No GPS route available for this activity.</p>;
  }

  return (
    <div style={{ height: 440, width: "100%" }}>
      <MapContainer
        center={positions[0]}
        zoom={12}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <Polyline
          positions={positions}
          pathOptions={{
            color: "#38bdf8",
            weight: 4,
          }}
        />

        <CircleMarker
          center={positions[0]}
          radius={7}
          pathOptions={{ color: "#22c55e" }}
        >
          <Popup>Start</Popup>
        </CircleMarker>

        <CircleMarker
          center={positions[positions.length - 1]}
          radius={7}
          pathOptions={{ color: "#ef4444" }}
        >
          <Popup>Finish</Popup>
        </CircleMarker>

        <FitBounds positions={positions} />
      </MapContainer>
    </div>
  );
}
