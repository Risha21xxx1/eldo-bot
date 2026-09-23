/**
 * Eldorado DOM selectors.
 * 
 * Centralized selector definitions for easy maintenance when Eldorado changes their UI.
 */

export const ELDORADO_SELECTORS = {
  // Order listing page
  order_card: '[data-order-card], .order-card, .listing-card',
  order_link: 'a.order-link, a[href*="/order/"], a[href*="/listing/"]',
  order_price: '.price, [data-price], .cost',
  order_title: '.title, h3, .order-title, .listing-title',
  region_badge: '.region, [data-region], .badge-region',
  
  // Single order page
  order_detail: '.order-detail, .listing-detail',
  order_id: '.order-id, [data-order-id]',
  order_type: '.order-type, .service-type',
  current_rank: '.current-rank, .from-rank',
  target_rank: '.target-rank, .to-rank',
  lp_amount: '.lp-amount, [data-lp]',
  queue_type: '.queue-type, .game-mode',
  
  // Buyer info
  buyer_username: '.buyer-name, .customer-name, [data-buyer]',
  buyer_description: '.buyer-description, .requirements, .notes',
  
  // Modifiers
  duo_required: '.duo-required, [data-duo="true"]',
  offline_mode: '.offline-mode, [data-offline="true"]',
  solo_queue: '.solo-queue, [data-solo="true"]',
  stream_required: '.stream-required, [data-stream="true"]',
  
  // Game counts
  requested_wins: '.wins-count, [data-wins]',
  requested_games: '.games-count, [data-games]',
  
  // Status indicators
  order_status: '.status, .order-status, .listing-status',
  availability: '.availability, .stock-status',
};
