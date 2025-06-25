// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";
import { post } from "aws-amplify/api";
import { getErrorMessage } from "./utils";
import { QueryObject,EmergencyCheckQuery } from "../types";
import { config } from "./config";

interface WorkOrderResponse {
  body: {
    json(): Promise<WorkOrder[]>;
  }
}

export interface WorkOrder {
  work_order_id: string;
  asset_id: string;
  description: string;
  location_name: string;
  owner_name: string;
  priority: number;
  safetycheckresponse: string
  safetyCheckPerformedAt: string;
  scheduled_start_timestamp: string;
  scheduled_finish_timestamp: string;
  status: string;
  location_details: {
    location_name: string;
    address: string;
    description: string;
    latitude: number;
    longitude: number;
  };
}

// WebSocket message interface
export interface WebSocketMessage {
  type: 'chunk' | 'trace' | 'status' | 'final' | 'error';
  content?: string | any;
  message?: string | WebSocketMessage;  // Handle nested message structure
  status?: string;
  traceType?: string;
  requestId?: string;
  safetyCheckResponse?: string;
  safetyCheckPerformedAt?: string;
  agentFramework?: string;  // Add agent framework information
}

// Use runtime config instead of env variables
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: config.COGNITO_USER_POOL_ID,
      userPoolClientId: config.COGNITO_USER_POOL_CLIENT_ID,
      identityPoolId: config.COGNITO_IDENTITY_POOL_ID,
      loginWith: {
        oauth: {
          domain: config.COGNITO_DOMAIN,
          scopes: ["openid", "email"],
          redirectSignIn: [config.APP_REDIRECT_SIGN_IN_URL],
          redirectSignOut: [config.APP_REDIRECT_SIGN_OUT_URL],
          responseType: 'code',
        },
      },
    },
  },
});

const existingConfig = Amplify.getConfig();

Amplify.configure({
  ...existingConfig,
  API: {
    REST: {
      [config.API_NAME]: {
        endpoint: config.API_ENDPOINT,
        region: config.REGION_NAME,
      },
      [config.WorkOrder_API_NAME]:{
        endpoint: config.WORKORDER_API_ENDPOINT,
        region: config.REGION_NAME,
      },
    },
  },
});

// Create a function to get auth token
const getAuthToken = async () => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (!token) {
      throw new Error('No auth token available');
    }
    return token;
  } catch (error) {
    console.error('Error getting auth token:', error);
    throw error;
  }
};
// Create a function to get REST input with fresh token
const getRestInput = async (apiName: string) => {
  const authToken = await getAuthToken();
  return {
    apiName,
    options: {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    },
  };
};


export async function postSafetyCheckRequest(queryObject: QueryObject) {
  try {
    const restInput = await getRestInput(config.API_NAME);
    const restOperation = post({
      ...restInput,
      path: `safetycheck/request`,
      options: {
        ...restInput.options,
        body: queryObject,
      },
    });
    console.log(restOperation)
    const response = await restOperation.response;
    console.log(response)
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}

interface WorkOrderResponse {
  body: {
    json(): Promise<WorkOrder[]>;
  }
}


export async function postWorkOrderQuery(): Promise<WorkOrder[]> {
  try {
    const restInput = await getRestInput(config.WorkOrder_API_NAME);
    const restOperation = post({
      ...restInput,
      path: `workorders`,
      options: {
        ...restInput.options,
        body: {} // Changed from empty string to empty object
      }
    });
    const response = await (restOperation.response as unknown) as WorkOrderResponse;
    
    // Add null check and provide default empty array
    return response.body.json() ?? [];
  } catch (e: unknown) {
    console.log("postWorkOrderQuery call failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function pollSafetyCheckStatus(requestId: string) {
  try {
      const restInput = await getRestInput(config.API_NAME);
      const restOperation = await post({
          ...restInput,
          path: `safetycheck/status`,
          options: {
              ...restInput.options,
              body: { requestId }
          }
      });
      const response = await restOperation.response;
    
      return response.body.json();
  } catch (e: unknown) {
      console.log("Status polling failed: ", getErrorMessage(e));
      throw e;
  }
}

export async function postEmergencyCheckRequest(queryObject: EmergencyCheckQuery) {
  try {
    const restInput = await getRestInput(config.API_NAME);
    const restOperation = post({
      ...restInput,
      path: `emergencycheck/request`,
      options: {
        ...restInput.options,
        body: queryObject,
      },
    });
    console.log(restOperation)
    const response = await restOperation.response;
    console.log(response)
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}

// WebSocket implementation
class SafetyCheckWebSocket {
  private socket: WebSocket | null = null;
  private messageHandlers: ((message: WebSocketMessage) => void)[] = [];
  private isConnected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor() {
    this.connect = this.connect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.sendMessage = this.sendMessage.bind(this);
    this.addMessageHandler = this.addMessageHandler.bind(this);
    this.removeMessageHandler = this.removeMessageHandler.bind(this);
  }

  public async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket && this.isConnected) {
        resolve();
        return;
      }

      try {
        // Use the WebSocket API endpoint from config
        const wsEndpoint = config.WEBSOCKET_API_ENDPOINT;
        if (!wsEndpoint) {
          reject(new Error('WebSocket API endpoint not configured'));
          return;
        }

        this.socket = new WebSocket(wsEndpoint);

        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          resolve();
        };

        this.socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WebSocketMessage;
            this.messageHandlers.forEach(handler => handler(message));
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.socket.onclose = () => {
          console.log('WebSocket disconnected');
          this.isConnected = false;
          this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          if (!this.isConnected) {
            reject(error);
          }
        };
      } catch (error) {
        console.error('Error connecting to WebSocket:', error);
        reject(error);
      }
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
      
      console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
      }
      
      this.reconnectTimeout = setTimeout(() => {
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isConnected = false;
      
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
      }
    }
  }

  public async sendMessage(action: string, data: any): Promise<void> {
    if (!this.socket || !this.isConnected) {
      throw new Error('WebSocket not connected');
    }

    // Get a fresh token using the existing getAuthToken function
    const token = await getAuthToken();

    const message = {
      action,
      token, // Include the token in every message
      ...data
    };

    this.socket.send(JSON.stringify(message));
  }

  public async performSafetyCheck(queryObject: any): Promise<void> {
    await this.sendMessage('safetyCheck', queryObject);
  }

  public addMessageHandler(handler: (message: WebSocketMessage) => void): void {
    this.messageHandlers.push(handler);
  }

  public removeMessageHandler(handler: (message: WebSocketMessage) => void): void {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  public isSocketConnected(): boolean {
    return this.isConnected;
  }
}

// Create a singleton instance
export const safetyCheckWebSocket = new SafetyCheckWebSocket();
