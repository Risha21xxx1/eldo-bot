/**
 * Extension background service worker.
 * 
 * Handles communication between content scripts, popup, options, and backend.
 */

import {
  ExtensionMessage,
  OrderSyncRequest,
  OrderSyncResponse,
  HealthCheckResponse,
  ApiResponse,
  EldoradoOrder,
} from '../shared/types';

// Configuration
let backendUrl = 'http://localhost:8000';
let apiKey = '';
let refreshInterval = 30; // seconds
let lastSyncTime: Date | null = null;

// Load settings on startup
chrome.storage.sync.get(
  ['backendUrl', 'apiKey', 'refreshInterval'],
  (result) => {
    if (result.backendUrl) backendUrl = result.backendUrl;
    if (result.apiKey) apiKey = result.apiKey;
    if (result.refreshInterval) refreshInterval = result.refreshInterval;
    
    // Start sync alarm
    startSyncAlarm();
  }
);

// Alarm for periodic syncing
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'order-sync') {
    performOrderSync();
  }
});

function startSyncAlarm(): void {
  chrome.alarms.create('order-sync', {
    periodInMinutes: Math.max(refreshInterval / 60, 1),
  });
}

// Message handler
chrome.runtime.onMessage.addListener(
  (message: ExtensionMessage, sender, sendResponse) => {
    handleMessage(message, sender).then(sendResponse);
    return true; // Keep message channel open for async response
  }
);

async function handleMessage(
  message: ExtensionMessage,
  sender: chrome.runtime.MessageSender
): Promise<unknown> {
  switch (message.type) {
    case 'HEALTH_CHECK':
      return await checkBackendHealth();
    
    case 'ORDERS_SYNC':
      return await syncOrders(message.payload as EldoradoOrder[]);
    
    case 'SETTINGS_UPDATE':
      return await updateSettings(message.payload as Record<string, unknown>);
    
    default:
      return { success: false, error: 'Unknown message type' };
  }
}

async function checkBackendHealth(): Promise<ApiResponse<HealthCheckResponse>> {
  try {
    const response = await fetch(`${backendUrl}/api/v1/health`);
    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Health check failed',
    };
  }
}

async function syncOrders(
  orders: EldoradoOrder[]
): Promise<ApiResponse<OrderSyncResponse>> {
  if (orders.length === 0) {
    return { success: true, data: { processed: 0, newOrders: [], updatedOrders: [], skippedOrders: [] } };
  }
  
  try {
    const request: OrderSyncRequest = {
      orders: orders,
      timestamp: new Date().toISOString(),
    };
    
    const response = await fetch(`${backendUrl}/api/v1/orders/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey ? { 'X-API-Key': apiKey } : {}),
      },
      body: JSON.stringify(request),
    });
    
    const data = await response.json();
    
    if (response.ok) {
      lastSyncTime = new Date();
      
      // Send notification if new orders were found
      if (data.newOrders && data.newOrders.length > 0) {
        showNotification(
          'New Orders Found',
          `${data.newOrders.length} new boosting order(s) detected!`
        );
      }
      
      return { success: true, data };
    } else {
      return { success: false, error: data.error || 'Sync failed' };
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Sync failed',
    };
  }
}

async function updateSettings(settings: Record<string, unknown>): Promise<ApiResponse<void>> {
  try {
    await chrome.storage.sync.set(settings);
    
    // Update local variables
    if (settings.backendUrl) backendUrl = settings.backendUrl as string;
    if (settings.apiKey) apiKey = settings.apiKey as string;
    if (settings.refreshInterval) {
      refreshInterval = settings.refreshInterval as number;
      startSyncAlarm();
    }
    
    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update settings',
    };
  }
}

async function performOrderSync(): Promise<void> {
  // Query active Eldorado tabs
  const tabs = await chrome.tabs.query({
    url: '*://*.eldorado.gg/*',
  });
  
  for (const tab of tabs) {
    if (tab.id) {
      try {
        await chrome.tabs.sendMessage(tab.id, { type: 'SYNC_ORDERS' });
      } catch (error) {
        // Content script may not be loaded yet
        console.log('Could not send sync message to tab:', tab.url);
      }
    }
  }
}

function showNotification(title: string, message: string): void {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title,
    message,
    priority: 1,
  });
}

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    // Open options page on first install
    chrome.runtime.openOptionsPage();
    
    // Show welcome notification
    showNotification(
      'Eldorado Boosting Assistant Installed',
      'Configure your settings in the options page.'
    );
  }
});
