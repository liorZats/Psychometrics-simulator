import { Platform } from 'react-native';
const webTargetOrigins = [
  "http://localhost:8081", // Your parent dev server
  "https://kiki.dev",       // Your production parent
  "http://localhost:3000", 
  // Add your Expo web preview origin if it's different (e.g., from Metro bundler)
  // Often something like "http://localhost:19006" or "http://localhost:8080"
];

// This function will be exported and used by the ErrorBoundary component later
export function sendErrorToIframeParent(errorSource: any, errorInfo?: { componentStack?: string } | React.ErrorInfo) {
  if (Platform.OS === 'web' && typeof window !== 'undefined' && window.parent && window.parent !== window) {
    console.debug('[GlobalErrorHandler] Attempting to send error to parent:', {
      errorSource,
      errorInfo,
      currentReferrer: document.referrer,
      currentOrigin: window.location.origin,
    });

    let message = 'Unknown error';
    let stack = undefined;
    let componentStack = (errorInfo as React.ErrorInfo)?.componentStack; // Type assertion for clarity

    if (errorSource instanceof Error) {
      message = errorSource.message;
      stack = errorSource.stack;
    } else if (typeof errorSource === 'string') {
      message = errorSource;
      try { throw new Error(message); } catch (e: any) { stack = e.stack; }
    } else if (errorSource && typeof errorSource.message === 'string') {
      message = errorSource.message;
      stack = errorSource.stack;
    } else {
      try {
        message = JSON.stringify(errorSource);
      } catch (e) {
        message = 'Could not stringify error source.';
      }
    }

    const errorMessagePayload = {
      type: 'ERROR',
      error: {
        message: message,
        stack: stack,
        componentStack: componentStack,
        timestamp: new Date().toISOString(),
      },
      iframeId: "kiki-web-preview",
    };

    let targetOrigin = '*';
    if (document.referrer) {
      try {
        const referrerURL = new URL(document.referrer);
        if (webTargetOrigins.includes(referrerURL.origin)) {
          targetOrigin = referrerURL.origin;
        } else {
          console.warn(`[GlobalErrorHandler] Referrer origin "${referrerURL.origin}" not in webTargetOrigins. Defaulting to '*' for postMessage. Valid targets:`, webTargetOrigins);
        }
      } catch (e) {
        console.warn('[GlobalErrorHandler] Could not parse document.referrer or determine target origin:', e, document.referrer);
      }
    } else {
        console.warn('[GlobalErrorHandler] document.referrer is empty. Defaulting to "*" for postMessage. This might happen if the iframe is navigated to directly or due to referrer policy.');
    }
    
    console.debug(`[GlobalErrorHandler] Using targetOrigin: "${targetOrigin}" for postMessage.`);

    try {
      window.parent.postMessage(errorMessagePayload, targetOrigin);
      console.debug('[GlobalErrorHandler] Error message posted to parent.', errorMessagePayload);
    } catch (postMessageError) {
      console.error('[GlobalErrorHandler] Failed to send error to parent via postMessage:', postMessageError);
    }
  } else if (Platform.OS === 'web') {
    let reason = "Not in an iframe (window.parent === window or window.parent is null)";
    if (!window.parent) reason = "window.parent is null";
    else if (window.parent === window) reason = "window.parent is the same as window (not in iframe)";
    console.debug(`[GlobalErrorHandler] Not sending to parent. Platform: ${Platform.OS}, Reason: ${reason}`);
  }
}

// Immediately setup global error handlers if on web
if (Platform.OS === 'web' && typeof window !== 'undefined') {
  console.log('[GlobalErrorHandler] Initializing global error listeners for web.');

  window.addEventListener('error', (event: ErrorEvent) => {
    console.log('[GlobalErrorHandler] Global window.onerror caught:', event);
    const error = event.error || new Error(event.message || 'Unknown error from window.onerror');
    // Attach additional info if available
    if(!error.hasOwnProperty('filename') && event.filename) (error as any).filename = event.filename;
    if(!error.hasOwnProperty('lineno') && event.lineno) (error as any).lineno = event.lineno;
    if(!error.hasOwnProperty('colno') && event.colno) (error as any).colno = event.colno;
    sendErrorToIframeParent(error, { componentStack: undefined });
    // Do not preventDefault yet, allow browser to also log it until confirmed working
  }, true); // Use capture phase

  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    console.log('[GlobalErrorHandler] Global unhandledrejection caught:', event);
    sendErrorToIframeParent(event.reason || 'Unhandled promise rejection', { componentStack: undefined });
  }, true); // Use capture phase

  const originalConsoleError = console.error;
  console.error = (...args: any[]) => {
    // Call original first so it always appears in the console
    originalConsoleError.apply(console, args);
    console.log('[GlobalErrorHandler] console.error intercepted:', args);
    const errorArg = args.find(arg => arg instanceof Error);
    if (errorArg) {
      sendErrorToIframeParent(errorArg);
    } else {
      const message = args.map(arg => {
        if (typeof arg === 'object' && arg !== null) {
          try { return JSON.stringify(arg); } catch (e) { return '[Unserializable Object]'; }
        }
        return String(arg);
      }).join(' ');
      sendErrorToIframeParent(message);
    }
  };
  console.log('[GlobalErrorHandler] Global error listeners initialized.');
} else {
  console.log(`[GlobalErrorHandler] Not initializing web error listeners. Platform: ${Platform.OS}, window: ${typeof window}`);
}