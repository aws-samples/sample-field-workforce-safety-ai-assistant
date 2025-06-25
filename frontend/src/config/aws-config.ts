export const awsConfig = {
    Auth: {
      region: import.meta.env.VITE_AWS_REGION,
      userPoolId: import.meta.env.VITE_USER_POOL_ID,
      userPoolWebClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
      mandatorySignIn: true,
      oauth: {
        domain: import.meta.env.VITE_COGNITO_DOMAIN,
        scope: ['email', 'openid', 'profile'],
        redirectSignIn: import.meta.env.VITE_REDIRECT_SIGNIN,
        redirectSignOut: import.meta.env.VITE_REDIRECT_SIGNOUT,
        responseType: 'code'
      }
    },
    API: {
      endpoints: [
        {
          name: 'WorkOrderAPI',
          endpoint: import.meta.env.VITE_API_ENDPOINT
        }
      ]
    }
  };
  