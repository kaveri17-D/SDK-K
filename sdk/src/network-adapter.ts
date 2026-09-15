import * as os from "os";
import { NetworkAdapter } from "./types";

/**
 * LocalNetworkAdapter provides the standard V1 baseline networking implementation,
 * inspecting local network interfaces without overlay dependencies.
 *
 * In V2, a TailscaleNetworkAdapter or HeadscaleNetworkAdapter can implement
 * the same NetworkAdapter interface to enable mesh/overlay networking.
 */
export class LocalNetworkAdapter implements NetworkAdapter {
  private isConnected: boolean = false;

  async connect(): Promise<void> {
    this.isConnected = true;
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
  }

  async getStatus(): Promise<{ connected: boolean; overlayAddress?: string }> {
    const address = await this.getOverlayAddress();
    return {
      connected: this.isConnected,
      overlayAddress: address || undefined,
    };
  }

  async getOverlayAddress(): Promise<string | null> {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
      for (const net of interfaces[name] || []) {
        // Skip internal/loopback and non-IPv4 for standard egress inspection
        if (!net.internal && net.family === "IPv4") {
          return net.address;
        }
      }
    }
    return null;
  }

  async getPeers(): Promise<string[]> {
    // In V1 local mode, overlay peers are empty
    return [];
  }
}
