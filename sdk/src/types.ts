export interface ClipperXSDKOptions {
  apiUrl: string;
  heartbeatIntervalMs?: number;
  stateFilePath?: string;
  deviceName?: string;
  capabilities?: Record<string, boolean>;
  networkAdapter?: NetworkAdapter;
  logger?: SDKLogger;
}

export interface SDKLogger {
  info(message: string, meta?: Record<string, any>): void;
  warn(message: string, meta?: Record<string, any>): void;
  error(message: string, meta?: Record<string, any>): void;
  debug(message: string, meta?: Record<string, any>): void;
}

export interface NodeInfo {
  nodeId: string;
  platform: string;
  sdkVersion: string;
  status: string;
  healthStatus: string;
  capabilities?: Record<string, any>;
  observedPublicIp?: string | null;
  downloadMbps?: number | null;
  uploadMbps?: number | null;
  lastHeartbeatAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface NetworkInfo {
  publicIp: string;
  observedAt: string;
  description: string;
}

export interface BandwidthResult {
  downloadMbps: number;
  bytes: number;
  durationMs: number;
  description: string;
}

export interface UploadBandwidthResult {
  uploadMbps: number;
  bytes: number;
  durationMs: number;
  description: string;
}

export interface NodeRegistrationResponse {
  nodeId: string;
  token: string;
  status: string;
  platform: string;
  sdkVersion: string;
}

export interface HeartbeatPayload {
  sdkVersion: string;
  timestamp: string;
  health: {
    network: boolean;
    [key: string]: any;
  };
}

export interface HeartbeatResult {
  status: string;
  acknowledgedAt: string;
  nodeId: string;
}

export interface ReportNetworkInfoRequest {
  observed_public_ip?: string;
  download_mbps?: number;
  upload_mbps?: number;
}

export interface NodeLocalState {
  nodeId: string;
  nodeToken: string;
  platform: string;
  sdkVersion: string;
  registeredAt: string;
}

export interface NetworkAdapter {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  getStatus(): Promise<{ connected: boolean; overlayAddress?: string }>;
  getOverlayAddress(): Promise<string | null>;
  getPeers(): Promise<string[]>;
}
