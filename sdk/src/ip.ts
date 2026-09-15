import { NetworkInfo } from "./types";
import { NetworkError } from "./errors";

/**
 * Fetches the observed public egress IP address.
 *
 * NOTE: As required by Clipper-X architectural guidelines, this value is
 * explicitly labeled as the public egress IP observed by the Clipper-X backend,
 * rather than a local-network socket discovery.
 */
export async function getPublicIP(apiUrl: string): Promise<NetworkInfo> {
  const endpoint = `${apiUrl.replace(/\/+$/, "")}/api/v1/network/ip`;

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to fetch public IP from backend: ${err.message}`);
  }

  if (!response.ok) {
    throw new NetworkError(`Public IP endpoint returned HTTP ${response.status}`, response.status);
  }

  const data: any = await response.json();
  return {
    publicIp: data.ip,
    observedAt: data.observed_at,
    description: "Observed public egress IP from the Clipper-X backend",
  };
}
