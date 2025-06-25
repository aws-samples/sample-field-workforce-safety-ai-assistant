export interface EmergencyProperties {
  status: string;
  feedType: string;
  sourceOrg: string;
  sourceId: number | string;
  sourceFeed: string;
  sourceTitle: string;
  id: number | string;
  category1: string;
  category2: string;
  created: string;
  updated: string;
  resources: number;
  size?: string;
  sizeFmt?: string;
  location: string;
  estaId?: number;
  cfaId?: number;
  mfbId?: string;
  sesId?: number;
  webHeadline?: string;
  webBody?: string;
  url?: string;
}

export interface EmergencyGeometry {
  type: 'Point' | 'Polygon' | 'GeometryCollection';
  coordinates: number[] | number[][][] | null;
  geometries?: Array<{
    type: string;
    coordinates: number[][] | number[][][];
    name?: string;
  }>;
}

export interface Emergency {
  type: 'Feature';
  properties: EmergencyProperties;
  geometry: EmergencyGeometry;
}


export interface UnifiedMapProps {
centerPoint: [number, number];
description: string; // Work order description
emergencies?: Emergency[]; // Emergencies data
}