import { useAuthenticator } from "@aws-amplify/ui-react";
import TopNavigation from "@cloudscape-design/components/top-navigation";
import { useEffect, useState } from "react";
import { fetchUserAttributes } from "aws-amplify/auth";
import { config } from "../lib/config";
import UserProfile from "./UserProfile";

// Define the type for user attributes
type UserAttributes = {
  email?: string;
  [key: string]: string | undefined;
};

export default function NavBar() {
  const { user, signOut } = useAuthenticator((context) => [context.user]);
  const [userAttributes, setUserAttributes] = useState<UserAttributes>({});
  const [showProfile, setShowProfile] = useState(false);

  // Update the type to match fetchUserAttributes output
  useEffect(() => {
    async function getUserAttributes() {
      try {
        const attributes = await fetchUserAttributes();
        setUserAttributes(attributes);
      } catch (error) {
        console.log('Error fetching user attributes:', error);
      }
    }
    
    if (user) {
      getUserAttributes();
    }
  }, [user]);

  const handleFrameworkChange = (framework: string) => {
    // Framework change is handled in UserProfile component
    // This could be used to trigger any global state updates if needed
    console.log('Framework changed to:', framework);
  };

  return (
    <>
      <TopNavigation
        identity={{
          href: "/",
          title: config.APP_NAME,
        }}
        utilities={[
          {
            type: "menu-dropdown",
            text: userAttributes?.email || "Customer Name",
            description: userAttributes?.email || "email@example.com",
            iconName: "user-profile",
            onItemClick: (item) => {
              if (item.detail.id === 'profile') {
                setShowProfile(true);
              } else if (item.detail.id === 'signout') {
                signOut();
              }
            },
            items: [
              { 
                id: "profile", 
                text: "Profile & Settings",
                iconName: "settings"
              },
              { 
                id: "signout", 
                text: "Sign out",
                iconName: "external"
              }
            ]
          }
        ]}
      />
      
      <UserProfile
        visible={showProfile}
        onDismiss={() => setShowProfile(false)}
        onFrameworkChange={handleFrameworkChange}
      />
    </>
  );
}
