import { MapContainer, TileLayer, Marker, Circle, Popup, Polygon} from 'react-leaflet';
import * as L from 'leaflet';
import type {LatLngTuple} from 'leaflet';
import 'leaflet/dist/leaflet.css';
// Default Leaflet marker icon fix
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { UnifiedMapProps } from '@/types/emergency';
const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = defaultIcon;
const UnifiedMap: React.FC<UnifiedMapProps> = ({ centerPoint, description, emergencies}) => {
  return (
    <MapContainer center={[centerPoint[1], centerPoint[0]]} zoom={13} style={{ height: '500px', width: '100%' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {/* Work Order Location */}
      <Marker position={[centerPoint[1], centerPoint[0]]}>
        <Popup>
          <strong>Work Order Location</strong>
          <br />
          {description}
        </Popup>
      </Marker>
      {/* Emergency Points */}
      {(emergencies ?? []).map((emergency) => {
        if (emergency.geometry.type === 'Point' && Array.isArray(emergency.geometry.coordinates)) {
          const coordinates: LatLngTuple = [
            emergency.geometry.coordinates[1] as number,
            emergency.geometry.coordinates[0] as number
          ];
                  return (
            <Circle
              key={emergency.properties.id}
              center={coordinates}
              radius={500}
              pathOptions={{
                color: getMarkerColor(emergency.properties.category1),
                fillColor: getMarkerColor(emergency.properties.category1),
                fillOpacity: 0.7
              }}
            >
              <Popup>
                <h3>{emergency.properties.category1}</h3>
                <p>
                  <strong>Status:</strong> {emergency.properties.status}
                </p>
                <p>
                  <strong>Location:</strong> {emergency.properties.location}
                </p>
                <p>
                  <strong>Source:</strong> {emergency.properties.sourceOrg}
                </p>
                <p>
                  <strong>Type:</strong> {emergency.properties.feedType}
                </p>
                {emergency.properties.size && (
                  <p>
                    <strong>Size:</strong> {emergency.properties.size}
                  </p>
                )}
                <p>
                  <strong>Updated:</strong> {new Date(emergency.properties.updated).toLocaleString()}
                </p>
              </Popup>
            </Circle>
          );
        }
        if (
            emergency.geometry.type === 'GeometryCollection' &&
            Array.isArray(emergency.geometry.geometries)
          ) {
            return emergency.geometry.geometries.map((geom, index) => {
                if (geom.type === 'Polygon' && Array.isArray(geom.coordinates)) {
                    const positions: LatLngTuple[] = (geom.coordinates[0] as number[][]).map((coord) => {
                      if (Array.isArray(coord) && coord.length >= 2) {
                        return [coord[1], coord[0]] as LatLngTuple; // Explicitly cast each coordinate pair to LatLngTuple
                      }
                      throw new Error('Invalid coordinate structure');
                    });
                    return (
                      <Polygon key={index} positions={positions}>
                        <Popup>
                          <strong>{emergency.properties.sourceTitle}</strong>
                          <br />
                          {emergency.properties.category2}
                        </Popup>
                      </Polygon>
                    );
                  }                            
              return null; // Skip invalid geometries
            });
          }
        return null;
      })}
    </MapContainer>
  );
};
// Utility function for marker color based on category
const getMarkerColor = (category: string): string => {
  switch (category.toLowerCase()) {
    case 'fire':
      return '#ff0000';
    case 'flooding':
      return '#0000ff';
    case 'tree down':
      return '#008000';
    case 'building damage':
      return '#ffa500';
    case 'met':
      return '#ffff00';
    default:
      return '#808080';
  }
};
export default UnifiedMap;
