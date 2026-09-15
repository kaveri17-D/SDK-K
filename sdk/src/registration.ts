import * as os from "os";
import { NodeRegistrationResponse } from "./types";
import { RegistrationError, NetworkError } from "./errors";

export interface RegisterOptions {
  platform?: string;
  sdkVersion?: string;
  deviceName?: string;
  capabilities?: Record<string, boolean>;
  ownerId?: string;
}

export async function registerNode(
  apiUrl: string,
  options: RegisterOptions = {}
): Promise<NodeRegistrationResponse> {
  const endpoint = `${apiUrl.replace(/\/+$/, "")}/api/v1/nodes/register`;

  const body = {
    platform: options.platform || os.platform(),
    sdk_version: options.sdkVersion || "1.0.0",
    device_name: options.deviceName || os.hostname(),
    capabilities: options.capabilities || {
      network: true,
      bandwidth_test: true,
      heartbeat: true,
    },
    owner_id: options.ownerId || null,
  };

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach Clipper-X registration endpoint: ${err.message}`);
  }

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new RegistrationError(
      `Registration failed with HTTP ${response.status}: ${errorText}`,
      response.status
    );
  }

  const data: any = await response.json();
  return {
    nodeId: data.node_id,
    token: data.token,
    status: data.status,
    platform: data.platform,
    sdkVersion: data.sdk_version,
  };
}
