import { HeartbeatResult, SDKLogger } from "./types";
import { AuthenticationError, AuthorizationError, HeartbeatError, NetworkError } from "./errors";

export type HeartbeatCallback = (result: HeartbeatResult) => void;
export type HeartbeatErrorCallback = (error: Error) => void;

export interface HeartbeatManagerOptions {
  apiUrl: string;
  nodeId: string;
  nodeToken: string;
  sdkVersion: string;
  intervalMs?: number;
  logger?: SDKLogger;
  onSuccess?: HeartbeatCallback;
  onError?: HeartbeatErrorCallback;
}

export class HeartbeatManager {
  private apiUrl: string;
  private nodeId: string;
  private nodeToken: string;
  private sdkVersion: string;
  private intervalMs: number;
  private timer: NodeJS.Timeout | null = null;
  private isRunningState: boolean = false;
  private consecutiveFailures: number = 0;
  private logger?: SDKLogger;
  private onSuccess?: HeartbeatCallback;
  private onError?: HeartbeatErrorCallback;
  private cachedEndpoint: string = "";
  private cachedHeaders: Record<string, string> = {};

  constructor(options: HeartbeatManagerOptions) {
    this.apiUrl = options.apiUrl.replace(/\/+$/, "");
    this.nodeId = options.nodeId;
    this.nodeToken = options.nodeToken;
    this.sdkVersion = options.sdkVersion;
    this.intervalMs = options.intervalMs || 30000;
    this.logger = options.logger;
    this.onSuccess = options.onSuccess;
    this.onError = options.onError;
    this.recomputeCached();
  }

  private recomputeCached(): void {
    this.cachedEndpoint = `${this.apiUrl}/api/v1/nodes/${encodeURIComponent(this.nodeId)}/heartbeat`;
    this.cachedHeaders = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this.nodeToken}`,
    };
  }

  public isRunning(): boolean {
    return this.isRunningState;
  }

  public updateCredentials(nodeId: string, nodeToken: string): void {
    this.nodeId = nodeId;
    this.nodeToken = nodeToken;
    this.recomputeCached();
  }

  /**
   * Starts periodic heartbeat timer.
   * Protects against duplicate timers: calling start() twice is safe and idempotent.
   */
  public start(): void {
    if (this.isRunningState) {
      this.logger?.debug("Heartbeat timer is already running; ignoring duplicate start.");
      return;
    }

    this.isRunningState = true;
    this.consecutiveFailures = 0;
    this.logger?.info(`Starting heartbeat service for ${this.nodeId} (interval: ${this.intervalMs}ms)`);

    // Fire initial heartbeat immediately
    this.sendPing().catch(() => {});

    // Schedule periodic loop
    this.scheduleNext(this.intervalMs);
  }

  /**
   * Stops heartbeat timer and cancels pending retry backoffs.
   */
  public stop(): void {
    if (!this.isRunningState) {
      return;
    }

    this.isRunningState = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.logger?.info(`Stopped heartbeat service for ${this.nodeId}`);
  }

  private scheduleNext(delayMs: number): void {
    if (!this.isRunningState) return;

    if (this.timer) {
      clearTimeout(this.timer);
    }

    this.timer = setTimeout(async () => {
      if (!this.isRunningState) return;
      try {
        await this.sendPing();
        this.consecutiveFailures = 0;
        this.scheduleNext(this.intervalMs);
      } catch (err: any) {
        this.consecutiveFailures++;
        // Bounded exponential backoff: min 2s, max intervalMs
        const backoffMs = Math.min(
          Math.pow(2, Math.min(this.consecutiveFailures, 5)) * 1000,
          this.intervalMs
        );
        this.logger?.warn(
          `Heartbeat failure #${this.consecutiveFailures}. Retrying in ${backoffMs}ms...`
        );
        this.scheduleNext(backoffMs);
      }
    }, delayMs);
  }

  /**
   * Sends a single heartbeat ping.
   */
  public async sendPing(): Promise<HeartbeatResult> {
    const payload = {
      sdk_version: this.sdkVersion,
      timestamp: new Date().toISOString(),
      health: {
        network: true,
      },
    };

    let response: Response;
    try {
      response = await fetch(this.cachedEndpoint, {
        method: "POST",
        headers: this.cachedHeaders,
        body: JSON.stringify(payload),
      });
    } catch (err: any) {
      const error = new NetworkError(`Heartbeat network request failed: ${err.message}`);
      this.onError?.(error);
      throw error;
    }

    if (response.status === 401) {
      const error = new AuthenticationError("Heartbeat rejected: invalid node credentials", 401);
      this.onError?.(error);
      throw error;
    }

    if (response.status === 403) {
      const error = new AuthorizationError("Heartbeat rejected: node ID mismatch or suspended", 403);
      this.onError?.(error);
      throw error;
    }

    if (!response.ok) {
      const error = new HeartbeatError(
        `Heartbeat failed with HTTP ${response.status}`,
        response.status
      );
      this.onError?.(error);
      throw error;
    }

    const data: any = await response.json();
    const result: HeartbeatResult = {
      status: data.status,
      acknowledgedAt: data.acknowledged_at,
      nodeId: data.node_id,
    };

    this.onSuccess?.(result);
    return result;
  }
}
