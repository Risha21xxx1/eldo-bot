/**
 * CSS selectors for Eldorado.gg DOM elements.
 * 
 * These selectors are used by the content script to extract order data.
 * Note: Selectors may need adjustment based on actual Eldorado.gg HTML structure.
 */

export const ELDORADO_SELECTORS = {
  // Order list page
  order_list: '.orders-list, .listings-grid, [data-testid="orders-list"]',
  order_card: '.order-card, .listing-card, [data-testid="order-card"]',
  order_link: '.order-link, .listing-link, a[href*="/order/"]',
  
  // Order details
  order_title: '.order-title, h1.listing-title, [data-testid="order-title"]',
  order_price: '.price-amount, .listing-price, [data-testid="order-price"]',
  order_currency: '.currency-symbol, .price-currency',
  
  // Rank information
  current_rank: '.current-rank, .from-rank, [data-testid="current-rank"]',
  target_rank: '.target-rank, .to-rank, [data-testid="target-rank"]',
  rank_tier: '.rank-tier, [data-testid="rank-tier"]',
  rank_division: '.rank-division, [data-testid="rank-division"]',
  rank_lp: '.lp-amount, [data-testid="rank-lp"]',
  
  // Requirements
  requirements_container: '.requirements, .boosting-options, [data-testid="requirements"]',
  duo_requirement: '[data-requirement="duo"], .duo-option, [data-testid="duo-required"]',
  offline_requirement: '[data-requirement="offline"], .offline-option, [data-testid="offline-mode"]',
  solo_requirement: '[data-requirement="solo"], .solo-queue-option, [data-testid="solo-queue"]',
  stream_requirement: '[data-requirement="stream"], .stream-option, [data-testid="stream-required"]',
  
  // Game counts
  wins_count: '.wins-count, .requested-wins, [data-testid="wins-count"]',
  games_count: '.games-count, .requested-games, [data-testid="games-count"]',
  
  // Buyer info
  buyer_username: '.buyer-username, .customer-name, [data-testid="buyer-username"]',
  buyer_description: '.order-description, .customer-notes, [data-testid="buyer-description"]',
  
  // Region and queue
  region_badge: '.region-badge, .server-region, [data-testid="region"]',
  queue_type: '.queue-type, .game-mode, [data-testid="queue-type"]',
  
  // Status
  order_status: '.order-status, .listing-status, [data-testid="order-status"]',
} as const;

/**
 * Helper function to query element safely.
 */
export function querySelectorSafe(
  parent: Element | Document,
  selector: string
): Element | null {
  const selectors = selector.split(',').map((s) => s.trim());
  
  for (const sel of selectors) {
    const element = parent.querySelector(sel);
    if (element) return element;
  }
  
  return null;
}

/**
 * Helper function to get text content safely.
 */
export function getTextContent(
  parent: Element | Document,
  selector: string,
  defaultValue = ''
): string {
  const element = querySelectorSafe(parent, selector);
  return element?.textContent?.trim() || defaultValue;
}
