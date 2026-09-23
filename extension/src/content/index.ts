/**
 * Content script for Eldorado.gg pages.
 * 
 * Scans the page for order information and sends it to the background worker.
 */

import { EldoradoOrder, ContentScriptMessage } from '../shared/types';
import { ELDORADO_SELECTORS } from '../selectors';

// Track scanned orders to avoid duplicates
const scannedOrderIds = new Set<string>();

// Listen for messages from background worker
chrome.runtime.onMessage.addListener(
  (message: { type: string }, sender, sendResponse) => {
    if (message.type === 'SYNC_ORDERS') {
      scanAndSendOrders();
    }
    return true;
  }
);

// Scan on page load
window.addEventListener('load', () => {
  setTimeout(scanAndSendOrders, 1000); // Delay to ensure DOM is ready
});

// Observe DOM changes for dynamic content
const observer = new MutationObserver(
  debounce(() => {
    scanAndSendOrders();
  }, 500)
);

observer.observe(document.body, {
  childList: true,
  subtree: true,
});

/**
 * Scan the page for orders and send to background worker.
 */
async function scanAndSendOrders(): Promise<void> {
  const orders = extractOrdersFromPage();
  
  if (orders.length > 0) {
    // Filter out already scanned orders
    const newOrders = orders.filter((order) => !scannedOrderIds.has(order.id));
    
    if (newOrders.length > 0 || orders.length > 0) {
      // Send all orders on each scan (backend handles deduplication)
      chrome.runtime.sendMessage({
        type: 'ORDERS_SCANNED',
        url: window.location.href,
        orders: orders,
      } as ContentScriptMessage);
      
      // Also send to background for syncing
      chrome.runtime.sendMessage({
        type: 'ORDERS_SYNC',
        payload: orders,
        timestamp: new Date().toISOString(),
      });
      
      // Mark as scanned
      orders.forEach((order) => scannedOrderIds.add(order.id));
    }
  }
}

/**
 * Extract orders from the current page.
 */
function extractOrdersFromPage(): EldoradoOrder[] {
  const orders: EldoradoOrder[] = [];
  
  // Check if we're on an order listing page
  const orderCards = document.querySelectorAll(ELDORADO_SELECTORS.order_card);
  
  if (orderCards.length > 0) {
    // Listing page - extract multiple orders
    orderCards.forEach((card) => {
      const order = extractOrderFromCard(card as HTMLElement);
      if (order) {
        orders.push(order);
      }
    });
  } else {
    // Check if we're on a single order page
    const orderData = extractSingleOrder();
    if (orderData) {
      orders.push(orderData);
    }
  }
  
  return orders;
}

/**
 * Extract order data from a card element.
 */
function extractOrderFromCard(card: HTMLElement): EldoradoOrder | null {
  try {
    const linkElement = card.querySelector(ELDORADO_SELECTORS.order_link) as HTMLAnchorElement;
    const url = linkElement?.href || window.location.href;
    const id = extractOrderIdFromUrl(url);
    
    if (!id) return null;
    
    const priceElement = card.querySelector(ELDORADO_SELECTORS.order_price);
    const priceText = priceElement?.textContent || '0';
    const price = parsePrice(priceText);
    
    const titleElement = card.querySelector(ELDORADO_SELECTORS.order_title);
    const title = titleElement?.textContent || '';
    
    return {
      id,
      url,
      type: parseOrderType(title),
      status: 'pending',
      price,
      currency: 'USD',
      region: parseRegion(card.querySelector(ELDORADO_SELECTORS.region_badge)?.textContent || ''),
      currentRank: { tier: 'Iron', division: null, lp: null },
      targetRank: { tier: 'Iron', division: null, lp: null },
      queueType: 'Solo/Duo',
      duoRequired: false,
      offlineMode: false,
      soloQueueOnly: false,
      streamRequired: false,
      requestedWins: null,
      requestedGames: null,
      buyerUsername: '',
      buyerDescription: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  } catch (error) {
    console.error('Error extracting order from card:', error);
    return null;
  }
}

/**
 * Extract single order data from detail page.
 */
function extractSingleOrder(): EldoradoOrder | null {
  try {
    const url = window.location.href;
    const id = extractOrderIdFromUrl(url);
    
    if (!id) return null;
    
    // TODO: Implement full single order extraction
    // This will be expanded when actual DOM parsing is implemented
    
    return {
      id,
      url,
      type: 'Ranked Solo',
      status: 'pending',
      price: 0,
      currency: 'USD',
      region: 'NA',
      currentRank: { tier: 'Iron', division: null, lp: null },
      targetRank: { tier: 'Iron', division: null, lp: null },
      queueType: 'Solo/Duo',
      duoRequired: false,
      offlineMode: false,
      soloQueueOnly: false,
      streamRequired: false,
      requestedWins: null,
      requestedGames: null,
      buyerUsername: '',
      buyerDescription: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  } catch (error) {
    console.error('Error extracting single order:', error);
    return null;
  }
}

/**
 * Extract order ID from URL.
 */
function extractOrderIdFromUrl(url: string): string | null {
  const match = url.match(/\/order\/([^/]+)/i) || url.match(/\/listing\/([^/]+)/i);
  return match ? match[1] : null;
}

/**
 * Parse price text to number.
 */
function parsePrice(priceText: string): number {
  const match = priceText.match(/\$?([\d,.]+)/);
  if (!match) return 0;
  return parseFloat(match[1].replace(/,/g, '')) || 0;
}

/**
 * Parse order type from title.
 */
function parseOrderType(title: string): EldoradoOrder['type'] {
  const lowerTitle = title.toLowerCase();
  
  if (lowerTitle.includes('flex')) return 'Ranked Flex';
  if (lowerTitle.includes('placement')) return 'Placement Games';
  if (lowerTitle.includes('win')) return 'Wins';
  if (lowerTitle.includes('game') && !lowerTitle.includes('placement')) return 'Games';
  if (lowerTitle.includes('coach')) return 'Coaching';
  
  return 'Ranked Solo';
}

/**
 * Parse region from text.
 */
function parseRegion(regionText: string): EldoradoOrder['region'] {
  const regions: Record<string, EldoradoOrder['region']> = {
    'NA': 'NA',
    'EUW': 'EUW',
    'EUNE': 'EUNE',
    'KR': 'KR',
    'BR': 'BR',
    'LAS': 'LAS',
    'LAN': 'LAN',
    'OCE': 'OCE',
    'RU': 'RU',
    'TR': 'TR',
    'JP': 'JP',
  };
  
  const upperText = regionText.toUpperCase();
  
  for (const [key, value] of Object.entries(regions)) {
    if (upperText.includes(key)) return value;
  }
  
  return 'NA'; // Default
}

/**
 * Debounce utility function.
 */
function debounce<T extends (...args: unknown[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
