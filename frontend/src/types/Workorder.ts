export interface WorkOrder {
    id: number;
    description: string;
    location: string;
    asset: number;
    status: string;
    scheduledStart: string;
    scheduledFinish: string;
    owner: string;
    priority: number;
    coordinates: [number, number];
  }
  
  export interface WorkOrderResponse {
    workOrders: WorkOrder[];
    total: number;
  }
  