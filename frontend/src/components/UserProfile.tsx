import React, { useState, useEffect } from 'react';
import {
  Modal,
  Box,
  SpaceBetween,
  Header,
  FormField,
  RadioGroup,
  Button,
  Alert,
  Popover,
  StatusIndicator
} from "@cloudscape-design/components";
import { useAuthenticator } from "@aws-amplify/ui-react";
import { fetchUserAttributes } from "aws-amplify/auth";

// Export the current framework - this is what other components will import
export let currentFramework: 'StrandsSDK' | 'BedrockAgent' = 'StrandsSDK';

// Load from localStorage on module load
const savedFramework = localStorage.getItem('preferredAgentFramework');
if (savedFramework === 'BedrockAgent' || savedFramework === 'StrandsSDK') {
  currentFramework = savedFramework;
}

interface UserProfileProps {
  visible: boolean;
  onDismiss: () => void;
  onFrameworkChange?: (framework: string) => void;
}

type UserAttributes = {
  email?: string;
  [key: string]: string | undefined;
};

type AgentFramework = 'StrandsSDK' | 'BedrockAgent';

interface FrameworkOption {
  value: AgentFramework;
  label: string;
  description: string;
  features: string[];
}

const frameworkOptions: FrameworkOption[] = [
  {
    value: 'StrandsSDK',
    label: 'Strands AI Agents',
    description: 'Open-source multi-agent framework for building conversational AI applications',
    features: [
      'Multi-agent orchestration with specialized roles',
      'Real-time streaming responses with detailed reasoning traces',
      'Flexible agent-as-tools pattern for complex workflows'
    ],
  },
  {
    value: 'BedrockAgent',
    label: 'Amazon Bedrock Agents',
    description: 'Fully managed service to build and deploy generative AI applications',
    features: [
      'Serverless and fully managed by AWS',
      'Built-in integration with AWS services and APIs',
      'Enterprise-grade security and compliance',
      'Automatic scaling and high availability'
    ],
  }
];

const UserProfile: React.FC<UserProfileProps> = ({
  visible,
  onDismiss,
  onFrameworkChange
}) => {
  const { user } = useAuthenticator((context) => [context.user]);
  const [userAttributes, setUserAttributes] = useState<UserAttributes>({});
  
  // Use simple local state initialized from the exported variable
  const [selectedFramework, setSelectedFramework] = useState<AgentFramework>(() => currentFramework);
  
  const [loading, setLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load user attributes
  useEffect(() => {
    async function loadUserData() {
      try {
        const attributes = await fetchUserAttributes();
        setUserAttributes(attributes);
        
        // Load current framework from localStorage
        const savedFramework = localStorage.getItem('preferredAgentFramework');
        if (savedFramework === 'BedrockAgent' || savedFramework === 'StrandsSDK') {
          setSelectedFramework(savedFramework);
          currentFramework = savedFramework; // Update exported variable
        }
        
      } catch (error) {
        console.log('Error loading user data:', error);
      }
    }
    
    if (user && visible) {
      loadUserData();
    }
  }, [user, visible]);

  const handleSave = async () => {
    setLoading(true);
    try {
      // Framework preference is already updated via setFramework() when RadioGroup changes
      
      // Notify parent component of framework change (for backward compatibility)
      if (onFrameworkChange) {
        onFrameworkChange(selectedFramework);
      }
      
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Error saving preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      onDismiss={onDismiss}
      visible={visible}
      header="User Profile & Settings"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Close
            </Button>
            <Button 
              variant="primary" 
              onClick={handleSave}
              loading={loading}
            >
              Save Preferences
            </Button>
          </SpaceBetween>
        </Box>
      }
      size="medium"
    >
      <SpaceBetween direction="vertical" size="l">
        {/* User Information */}
        <Box>
          <Header variant="h3">Account Information</Header>
          <SpaceBetween direction="vertical" size="s">
            <Box>
              <strong>Username:</strong> {user?.username}
            </Box>
            <Box>
              <strong>Email:</strong> {userAttributes?.email || 'Not available'}
            </Box>
          </SpaceBetween>
        </Box>

        {/* Success Alert */}
        {saveSuccess && (
          <Alert type="success" dismissible onDismiss={() => setSaveSuccess(false)}>
            Preferences saved successfully!
          </Alert>
        )}

        {/* Advanced Settings */}
        <Box>
          <Header 
            variant="h3"
            description="Configure advanced options for your safety analysis experience"
          >
            Advanced Settings
          </Header>
          
          <SpaceBetween direction="vertical" size="m">
            <FormField
              label={
                <SpaceBetween direction="horizontal" size="xs">
                  <span>AI Framework Selection</span>
                  <Popover
                    dismissButton={false}
                    position="top"
                    size="medium"
                    triggerType="custom"
                    content={
                      <Box>
                        <Header variant="h4">Framework Comparison</Header>
                        <SpaceBetween direction="vertical" size="s">
                          <Box>
                            <strong>Strands AI Agents:</strong> Best for complex analysis requiring 
                            multiple specialized agents working together. Offers real-time progress 
                            tracking and advanced error handling.
                          </Box>
                          <Box>
                            <strong>Amazon Bedrock Agents:</strong> Ideal for enterprise environments 
                            requiring AWS managed Agent experience.
                          </Box>
                          <Box>
                            <em>Note: You can change this setting anytime. The selected framework 
                            will be used for all future safety analyses.</em>
                          </Box>
                        </SpaceBetween>
                      </Box>
                    }
                  >
                    <Button variant="icon" iconName="status-info" />
                  </Popover>
                </SpaceBetween>
              }
              description="Choose the AI framework for safety analysis. This affects how your safety reports are generated and the features available."
            >
              <RadioGroup
                onChange={({ detail }) => {
                  const newFramework = detail.value as AgentFramework;
                  setSelectedFramework(newFramework);
                  currentFramework = newFramework; // Update exported variable immediately
                  localStorage.setItem('preferredAgentFramework', newFramework); // Save to localStorage
                }}
                value={selectedFramework}
                items={frameworkOptions.map(option => ({
                  value: option.value,
                  label: (
                    <SpaceBetween direction="vertical" size="xs">
                      <SpaceBetween direction="horizontal" size="s">
                        <strong>{option.label}</strong>
                      </SpaceBetween>
                      <Box fontSize="body-s" color="text-body-secondary">
                        {option.description}
                      </Box>
                      <Box fontSize="body-s">
                        <strong>Key Features:</strong>
                        <ul style={{ marginLeft: '16px', marginTop: '4px' }}>
                          {option.features.map((feature, index) => (
                            <li key={index}>{feature}</li>
                          ))}
                        </ul>
                      </Box>
                    </SpaceBetween>
                  ),
                  description: ''
                }))}
              />
            </FormField>
          </SpaceBetween>
        </Box>

        {/* Framework Performance Info */}
        <Alert type="info" header="Performance Information">
          <SpaceBetween direction="vertical" size="s">
            <Box>
              <strong>Current Selection:</strong> {frameworkOptions.find(opt => opt.value === selectedFramework)?.label}
            </Box>
            <Box>
              Your framework preference is saved for current session and will be used for all safety analyses. 
              You can change this setting anytime from your profile.
            </Box>
          </SpaceBetween>
        </Alert>
      </SpaceBetween>
    </Modal>
  );
};

export default UserProfile;
