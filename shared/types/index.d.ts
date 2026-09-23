/**
 * Shared type definitions between extension and backend
 */
export type LoLRank = 'Iron' | 'Bronze' | 'Silver' | 'Gold' | 'Platinum' | 'Emerald' | 'Diamond' | 'Master' | 'Grandmaster' | 'Challenger';
export type LoLDivision = 'I' | 'II' | 'III' | 'IV';
export type QueueType = 'Solo/Duo' | 'Flex' | 'Normal Draft' | 'Blind Pick';
export type Region = 'NA' | 'EUW' | 'EUNE' | 'KR' | 'BR' | 'LAS' | 'LAN' | 'OCE' | 'RU' | 'TR' | 'JP' | 'VN' | 'PH' | 'SG' | 'TH' | 'TW';
export type OrderType = 'Ranked Solo' | 'Ranked Flex' | 'Placement Games' | 'Wins' | 'Games' | 'Coaching';
export type OrderStatus = 'pending' | 'active' | 'completed' | 'cancelled' | 'disputed';
export interface RankInfo {
    tier: LoLRank;
    division: LoLDivision | null;
    lp: number | null;
}
export interface EldoradoOrder {
    id: string;
    url: string;
    type: OrderType;
    status: OrderStatus;
    price: number;
    currency: string;
    region: Region;
    currentRank: RankInfo;
    targetRank: RankInfo;
    queueType: QueueType;
    duoRequired: boolean;
    offlineMode: boolean;
    soloQueueOnly: boolean;
    streamRequired: boolean;
    requestedWins: number | null;
    requestedGames: number | null;
    buyerUsername: string;
    buyerDescription: string | null;
    createdAt: string;
    updatedAt: string;
}
export interface FilterConfig {
    enabled: boolean;
    minPrice: number | null;
    maxPrice: number | null;
    regions: Region[];
    orderTypes: OrderType[];
    minCurrentRank: LoLRank | null;
    maxCurrentRank: LoLRank | null;
    minTargetRank: LoLRank | null;
    maxTargetRank: LoLRank | null;
    requireDuo: boolean | null;
    requireOffline: boolean | null;
    requireSolo: boolean | null;
    requireStream: boolean | null;
    keywords: string[];
    excludeKeywords: string[];
}
export interface PricingConfig {
    basePricePerLP: number;
    rankMultipliers: Record<LoLRank, number>;
    duoMultiplier: number;
    offlineMultiplier: number;
    rushMultiplier: number;
    minOrderValue: number;
}
export interface DiscordConfig {
    enabled: boolean;
    webhookUrl: string | null;
    notifyOnNewOrder: boolean;
    notifyOnStatusChange: boolean;
    notifyOnPriceChange: boolean;
    pingRoles: string[];
    pingUsers: string[];
}
export interface ExtensionSettings {
    backendUrl: string;
    apiKey: string;
    refreshIntervalSeconds: number;
    enableNotifications: boolean;
    filterConfig: FilterConfig;
    pricingConfig: PricingConfig;
    discordConfig: DiscordConfig;
}
export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}
export interface OrderSyncRequest {
    orders: EldoradoOrder[];
    timestamp: string;
}
export interface OrderSyncResponse {
    processed: number;
    newOrders: string[];
    updatedOrders: string[];
    skippedOrders: string[];
}
export interface HealthCheckResponse {
    status: 'healthy' | 'degraded' | 'unhealthy';
    version: string;
    database: 'connected' | 'disconnected';
    discord: 'configured' | 'not_configured';
    timestamp: string;
}
export type MessageType = 'ORDER_DETECTED' | 'ORDERS_SYNC' | 'SETTINGS_UPDATE' | 'HEALTH_CHECK' | 'NOTIFICATION' | 'ERROR';
export interface ExtensionMessage<T = unknown> {
    type: MessageType;
    payload: T;
    timestamp: string;
}
export interface ContentScriptMessage {
    type: 'PAGE_LOADED' | 'ORDER_FOUND' | 'ORDERS_SCANNED';
    url: string;
    orders?: EldoradoOrder[];
}
export interface BackgroundMessage {
    type: 'SYNC_ORDERS' | 'UPDATE_SETTINGS' | 'SEND_NOTIFICATION';
    data?: unknown;
}
export interface PopupMessage {
    type: 'GET_STATUS' | 'GET_ORDERS' | 'OPEN_OPTIONS';
}
export interface NotificationData {
    title: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
    orderId?: string;
    orderUrl?: string;
}
//# sourceMappingURL=index.d.ts.map