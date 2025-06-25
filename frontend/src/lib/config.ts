// Configuration helper to get values from runtime config or fallback to env vars
declare global {
  interface Window {
    APP_CONFIG: {
      VITE_API_ENDPOINT: string;
      VITE_WORKORDER_API_ENDPOINT: string;
      VITE_WEBSOCKET_API_ENDPOINT: string;
      VITE_REGION_NAME: string;
      VITE_COGNITO_USER_POOL_ID: string;
      VITE_COGNITO_USER_POOL_CLIENT_ID: string;
      VITE_COGNITO_IDENTITY_POOL_ID: string;
      VITE_API_NAME: string;
      VITE_APP_NAME: string;
      VITE_WorkOrder_API_NAME: string;
      VITE_PROTOTYPE_NAME: string;
      VITE_COGNITO_DOMAIN: string;
      VITE_APP_REDIRECT_SIGN_IN_URL: string;
      VITE_APP_REDIRECT_SIGN_OUT_URL: string;
    };
  }
}

// Get config value from runtime config or fallback to env var
export function getConfig(key: string): string {
  // First try to get from runtime config
  if (window.APP_CONFIG && window.APP_CONFIG[key as keyof typeof window.APP_CONFIG]) {
    return window.APP_CONFIG[key as keyof typeof window.APP_CONFIG];
  }
  
  // Fallback to env vars (for development)
  return '';
}

// Export all config values
export const config = {
  API_ENDPOINT: getConfig('VITE_API_ENDPOINT'),
  WORKORDER_API_ENDPOINT: getConfig('VITE_WORKORDER_API_ENDPOINT'),
  WEBSOCKET_API_ENDPOINT: getConfig('VITE_WEBSOCKET_API_ENDPOINT'),
  REGION_NAME: getConfig('VITE_REGION_NAME'),
  COGNITO_USER_POOL_ID: getConfig('VITE_COGNITO_USER_POOL_ID'),
  COGNITO_USER_POOL_CLIENT_ID: getConfig('VITE_COGNITO_USER_POOL_CLIENT_ID'),
  COGNITO_IDENTITY_POOL_ID: getConfig('VITE_COGNITO_IDENTITY_POOL_ID'),
  API_NAME: getConfig('VITE_API_NAME'),
  APP_NAME: getConfig('VITE_APP_NAME'),
  WorkOrder_API_NAME: getConfig('VITE_WorkOrder_API_NAME'),
  PROTOTYPE_NAME: getConfig('VITE_PROTOTYPE_NAME'),
  COGNITO_DOMAIN: getConfig('VITE_COGNITO_DOMAIN'),
  AWS_REGION: getConfig('VITE_REGION_NAME'), 
  APP_REDIRECT_SIGN_IN_URL: getConfig('VITE_APP_REDIRECT_SIGN_IN_URL'),
  APP_REDIRECT_SIGN_OUT_URL: getConfig('VITE_APP_REDIRECT_SIGN_OUT_URL'),
};

export default config;