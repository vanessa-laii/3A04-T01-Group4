import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'

interface SensorMarker {
  id: string
  lat: number
  lng: number
  zone: string
  status: 'normal' | 'warning' | 'alert'
}

// Mock sensor locations around Hamilton, ON (McMaster area)
const MOCK_SENSORS: SensorMarker[] = [
  { id: 'S001', lat: 43.2557, lng: -79.9188, zone: 'Zone A', status: 'normal' },
  { id: 'S002', lat: 43.2610, lng: -79.9230, zone: 'Zone B', status: 'warning' },
  { id: 'S003', lat: 43.2490, lng: -79.9100, zone: 'Zone C', status: 'normal' },
  { id: 'S004', lat: 43.2680, lng: -79.9050, zone: 'Zone D', status: 'alert' },
  { id: 'S005', lat: 43.2540, lng: -79.9320, zone: 'Zone E', status: 'normal' },
  { id: 'S006', lat: 43.2720, lng: -79.9150, zone: 'Zone F', status: 'warning' },
  { id: 'S007', lat: 43.2430, lng: -79.9270, zone: 'Zone G', status: 'normal' },
]

const STATUS_COLOR: Record<SensorMarker['status'], string> = {
  normal: '#ffffff',
  warning: '#aaaaaa',
  alert: '#555555',
}

export default function MapView() {
  return (
    <MapContainer
      center={[43.257, -79.919]}
      zoom={13}
      className="w-full h-full"
      zoomControl={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {MOCK_SENSORS.map((sensor) => (
        <CircleMarker
          key={sensor.id}
          center={[sensor.lat, sensor.lng]}
          radius={6}
          pathOptions={{
            color: STATUS_COLOR[sensor.status],
            fillColor: STATUS_COLOR[sensor.status],
            fillOpacity: 0.9,
            weight: 1,
          }}
        >
          <Tooltip direction="top" offset={[0, -8]}>
            <span className="text-xs">
              {sensor.id} · {sensor.zone} · {sensor.status.toUpperCase()}
            </span>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
