import React, { useEffect, useState, useRef } from 'react';
import { safetyCheckWebSocket, WebSocketMessage } from '@/lib/api';
import { customAlphabet } from 'nanoid';
import { Button, SpaceBetween, Box, Spinner } from "@cloudscape-design/components";
import { currentFramework } from '@/components/UserProfile';
import './WebSocketSafetyCheck.css';

interface WebSocketSafetyCheckProps {
  workOrder: any;
  onSafetyCheckComplete: (response: string, timestamp?: string) => void;
  onSafetyCheckError: (error: string) => void;
  showResults?: boolean; // Optional prop to control whether to show results in this component
}

const WebSocketSafetyCheck: React.FC<WebSocketSafetyCheckProps> = ({
  workOrder,
  onSafetyCheckComplete,
  onSafetyCheckError,
  showResults = false // Default to not showing results in this component
}) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [traceContent, setTraceContent] = useState<string>("");
  const [currentChunk, setCurrentChunk] = useState<string>("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [finalResponseReceived, setFinalResponseReceived] = useState(false);
  
  // Use the framework directly from UserProfile
  const [agentFramework, setAgentFramework] = useState<string>(() => currentFramework);
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // No need for storage listener since we're using context

  // Refresh framework when component mounts
  useEffect(() => {
    setAgentFramework(currentFramework);
  }, []);

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      // Check if the message is in the nested format
      const webSocketMessage = message.message ? message.message : message;
      
      // Also check for framework in nested message (for display purposes only)
      const messageType = webSocketMessage.type;

      switch (messageType) {
        case 'chunk':
          if (webSocketMessage.content) {
            setCurrentChunk(prev => prev + webSocketMessage.content);
          }
          break;
        case 'trace':
          // Process trace message based on agent framework
          handleTraceMessage(message);
          break;
        case 'final':
          // Process final message (works for both Bedrock Agent and Strands)
          handleFinalMessage(webSocketMessage);
          break;
        case 'error':
          // Reset states on error
          setIsProcessing(false);
          setIsConnecting(false);
          onSafetyCheckError(webSocketMessage.safetyCheckResponse || webSocketMessage.content || 'Unknown error');
          break;
      }
    };

    // Add message handler
    safetyCheckWebSocket.addMessageHandler(handleMessage);

    // Cleanup
    return () => {
      safetyCheckWebSocket.removeMessageHandler(handleMessage);
      
      // Clear timeout when component unmounts
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [onSafetyCheckComplete, onSafetyCheckError]);

  const handleTraceMessage = (message: WebSocketMessage) => {
    // Extract the actual message content (handle nested structure)
    const webSocketMessage = message.message ? message.message : message;
    const content = webSocketMessage.content;
    
    if (!content) return;
    
    // Handle different trace formats based on agent framework
    let rationale = null;
    
    // Determine framework from trace structure for parsing (don't update state)
    let framework = agentFramework; // Use current framework setting
    
    if (framework === 'StrandsSDK') {
      // Handle Strands trace format: content.trace.orchestrationTrace.invocationInput.text
      if (content.trace?.orchestrationTrace?.invocationInput?.text) {
        rationale = content.trace.orchestrationTrace.invocationInput.text;
      } else if (typeof content === 'string') {
        rationale = content;
      }
    } else {
      // Handle Bedrock Agent trace format: content.trace.orchestrationTrace.rationale.text
      if (content.trace?.orchestrationTrace?.rationale?.text) {
        rationale = content.trace.orchestrationTrace.rationale.text;
      }
    }
    
    // Only add to trace content if we have a rationale
    if (rationale) {
      // Append the new rationale to the existing trace content
      setTraceContent(prev => {
        // Add a separator if there's already content
        const separator = prev ? '\n\n' : '';
        const newContent = prev + separator + rationale;
        return newContent;
      });
    }
  };

  const handleFinalMessage = (message: WebSocketMessage) => {
    // Mark that we've received the final response
    setFinalResponseReceived(true);
    
    // Reset processing state
    setIsProcessing(false);
    setIsConnecting(false);
    
    // Clear the timeout when we receive the final response
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    // Extract the final response - check both direct and nested formats
    let finalResponse = message.safetyCheckResponse || '';
    
    // Extract the safetyCheckPerformedAt timestamp if available
    const timestamp = message.safetyCheckPerformedAt || null;
    
    if (finalResponse) {
      // Clean up the final response
      finalResponse = cleanupFinalResponse(finalResponse);
      
      // Set the current chunk to show the final response (if we're showing results in this component)
      setCurrentChunk(finalResponse);
      
      // Call the completion callback with the cleaned response and timestamp
      if (timestamp) {
        onSafetyCheckComplete(finalResponse, timestamp);
      } else {
        onSafetyCheckComplete(finalResponse);
      }
    } else {
      onSafetyCheckError('No response received from safety check');
    }
  };

  // Function to clean up the final response
  const cleanupFinalResponse = (response: any): string => {
    try {
      // Handle object response (convert to string first)
      let responseText = '';
      
      if (typeof response === 'object') {
        // Handle Strands response structure: {"role":"assistant","content":[{"text":"..."}]}
        if (response.role === 'assistant' && response.content && Array.isArray(response.content)) {
          // Extract text from content array
          for (const contentItem of response.content) {
            if (contentItem.text) {
              responseText += contentItem.text;
            } else if (typeof contentItem === 'string') {
              responseText += contentItem;
            }
          }
        }
        // Check for nested content array structure: safetyCheckResponse.content[]
        else if (response.content && Array.isArray(response.content)) {
          // Extract text from content array
          for (const contentItem of response.content) {
            if (contentItem.type === 'text' && contentItem.text) {
              responseText += contentItem.text;
            } else if (contentItem.text) {
              responseText += contentItem.text;
            } else if (typeof contentItem === 'string') {
              responseText += contentItem;
            }
          }
        }
        // Fallback: check for direct response field
        else if (response.response) {
          responseText = response.response;
        }
        // Alternative: check for message field
        else if (response.message) {
          responseText = response.message;
        }
        // Last resort: stringify the object
        else {
          responseText = JSON.stringify(response);
        }
      } else {
        responseText = String(response);
      }
      
      // If no meaningful content extracted, return as-is
      if (!responseText || responseText.trim() === '') {
        return typeof response === 'string' ? response : JSON.stringify(response);
      }
      
      // Clean up formatting issues
      responseText = responseText
        .replace(/\\n/g, '')           // Remove literal \n
        .replace(/\n/g, ' ')           // Replace actual newlines with spaces
        .replace(/\r/g, '')            // Remove carriage returns
        .replace(/\t/g, ' ')           // Replace tabs with spaces
        .replace(/\s+/g, ' ')          // Replace multiple spaces with single space
        .trim();                       // Remove leading/trailing whitespace
      
      // Remove trailing characters like '}]}'
      responseText = responseText.replace(/[}\]]+$/, '');
      
      // Remove leading/trailing quotes
      responseText = responseText.replace(/^["']+|["']+$/g, '');
      
      // Check if there's any HTML content at all
      if (!responseText.includes('<') || !responseText.includes('>')) {
        return responseText; // No HTML tags at all, return as is
      }
      
      // Find the start of HTML content
      const htmlStartPatterns = ['<div', '<html', '<body', '<section', '<h1'];
      let startIndex = -1;
      
      for (const pattern of htmlStartPatterns) {
        const index = responseText.indexOf(pattern);
        if (index !== -1) {
          if (startIndex === -1 || index < startIndex) {
            startIndex = index;
          }
        }
      }
      
      if (startIndex > 0) {
        responseText = responseText.substring(startIndex);
      }
      
      // Remove any text before the first HTML tag using regex
      responseText = responseText.replace(/^[^<]*(?=<)/, '');
      
      // Find the end of HTML content (last closing tag)
      const lastTagMatch = responseText.match(/<\/[^>]+>(?=[^<]*$)/);
      if (lastTagMatch && lastTagMatch.index !== undefined) {
        responseText = responseText.substring(0, lastTagMatch.index + lastTagMatch[0].length);
      }
      
      // Ensure we have valid HTML structure
      const hasHtmlStructure = /<[a-z][^>]*>.*<\/[a-z][^>]*>/is.test(responseText);
      if (!hasHtmlStructure && responseText.includes('<')) {
        responseText = `<div>${responseText}</div>`;
      }
      
      return responseText;
    } catch (error) {
      console.error('Error cleaning up response:', error);
      // Return string representation of original response on error
      return typeof response === 'object' ? JSON.stringify(response) : String(response);
    }
  };

  const performSafetyCheck = async () => {
    try {
      // Get fresh framework value directly from UserProfile
      setAgentFramework(currentFramework);
      
      // Reset state
      setIsProcessing(true);
      setTraceContent("");
      setCurrentChunk("");
      setAuthError(null);
      setFinalResponseReceived(false);

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      // Connect to WebSocket if not already connected
      if (!safetyCheckWebSocket.isSocketConnected()) {
        setIsConnecting(true);
        try {
          await safetyCheckWebSocket.connect();
        } catch (error) {
          // Make sure to reset connecting state on connection error
          setIsConnecting(false);
          setIsProcessing(false);
          throw error; // Re-throw to be caught by the outer catch
        }
        setIsConnecting(false);
      }

      const queryObject = {
        workOrderDetails: {
          work_order_id: workOrder.work_order_id,
          latitude: workOrder.location_details?.latitude,
          longitude: workOrder.location_details?.longitude,
          target_datetime: workOrder.scheduled_start_timestamp,
        },
        agentFramework: currentFramework, // Use fresh framework value
        session_id: customAlphabet("1234567890", 20)()
      };

      // The token will be automatically included by the WebSocket class
      await safetyCheckWebSocket.performSafetyCheck(queryObject);
      
      // Set timeout AFTER the request is sent - this is important
      // We don't want the timeout to start during connection setup
      timeoutRef.current = setTimeout(() => {
        console.log("Safety check timeout triggered");
        if (isProcessing && !finalResponseReceived) {
          console.log("Safety check timed out - still processing and no final response");
          setIsProcessing(false);
          setIsConnecting(false);
          onSafetyCheckError('Error in performing safety check');
        } else {
          console.log("Safety check timeout fired but operation already completed");
        }
      }, 120000); // 2 min timeout
      
    } catch (error: any) {
      console.error('Error sending safety check request:', error);
      
      // Always reset both states on any error
      setIsConnecting(false);
      setIsProcessing(false);
      
      // Clear timeout on error
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      
      // Check if it's an authentication error
      if (error.message && error.message.includes('authentication')) {
        setAuthError('Authentication failed. Please sign in again.');
        onSafetyCheckError('Authentication failed');
      } else {
        onSafetyCheckError(`Failed to send safety check request: ${error.message || 'Unknown error'}`);
      }
    }
  };

  return (
    <SpaceBetween direction="vertical" size="m">
      {authError && (
        <Box variant="error">
          {authError}
        </Box>
      )}
      
      <Button 
        onClick={performSafetyCheck} 
        loading={isConnecting || isProcessing}
        variant="primary"
        disabled={isProcessing || isConnecting}
      >
        {isConnecting ? 'Connecting...' : isProcessing ? 
          (agentFramework === 'StrandsSDK' ? 'Processing with Strands...' : 'Performing Safety Check...') : 
          'Perform Safety Check'}
      </Button>
      
      {(isProcessing || (finalResponseReceived && showResults)) && (
        <div className="trace-container">
          {isProcessing && (
            <h3 className="section-heading-processing">
              Processing Safety Check {agentFramework === 'StrandsSDK' ? '(Strands Agent)' : '(Bedrock Agent)'}
            </h3>
          )}
          {finalResponseReceived && showResults && (
            <h3 className="section-heading-complete">
              Safety Check Complete {agentFramework === 'StrandsSDK' ? '(Strands Agent)' : '(Bedrock Agent)'}
            </h3>
          )}

          
          {/* Single continuous trace block */}
          <div className="agent-reasoning">
            <h4 className="subsection-heading">
              {agentFramework === 'StrandsSDK' ? 'Strands Agent Processing' : 'Bedrock Agent Reasoning'}
            </h4>
            {traceContent ? (
              <div className="trace-content">
                {traceContent.split('\n\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            ) : (
              <p>
                {agentFramework === 'StrandsSDK' ? 
                  'Strands agent is processing your request...' : 
                  'Bedrock agent is analyzing your request...'}
              </p>
            )}
          </div>
          
          {/* Only show the response here if showResults is true */}
          {currentChunk && showResults && (
            <div className="current-response">
              <h4 className="subsection-heading">Safety Briefing Response</h4>
              <div 
                className="response-text" 
                dangerouslySetInnerHTML={{ __html: currentChunk }}
              />
            </div>
          )}
          
          {isProcessing && (
            <div className="processing-indicator">
              <Spinner size="normal" /> 
              {agentFramework === 'StrandsSDK' ? 'Strands agent processing...' : 'Bedrock agent processing...'}
            </div>
          )}
        </div>
      )}
    </SpaceBetween>
  );
};

export default WebSocketSafetyCheck;