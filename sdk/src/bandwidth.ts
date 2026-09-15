import { BandwidthResult, UploadBandwidthResult } from "./types";
import { BandwidthError, NetworkError } from "./errors";

export async function measureDownloadBandwidth(
  apiUrl: string,
  sizeMb?: number
): Promise<BandwidthResult> {
  const url = new URL(`${apiUrl.replace(/\/+$/, "")}/api/v1/network/speed-test`);
  if (sizeMb && sizeMb > 0) {
    url.searchParams.set("size_mb", sizeMb.toString());
  }

  let response: Response;
  const startTime = performance.now();

  try {
    response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        Accept: "application/octet-stream",
        "Cache-Control": "no-cache",
      },
    });
  } catch (err: any) {
    throw new NetworkError(`Speed-test connection failed: ${err.message}`);
  }

  if (!response.ok) {
    throw new BandwidthError(`Speed-test failed with HTTP ${response.status}`, response.status);
  }

  if (!response.body) {
    throw new BandwidthError("Speed-test response has no body stream");
  }

  let bytesReceived = 0;
  const reader = response.body.getReader();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) {
      bytesReceived += value.byteLength;
    }
  }

  const endTime = performance.now();
  const durationMs = Math.max(endTime - startTime, 1);
  const elapsedSeconds = durationMs / 1000;
  const bits = bytesReceived * 8;
  const downloadMbps = Number((bits / elapsedSeconds / 1_000_000).toFixed(2));

  return {
    downloadMbps,
    bytes: bytesReceived,
    durationMs: Math.round(durationMs),
    description: "Observed bandwidth to Clipper-X test server",
  };
}

const UPLOAD_CHUNK_SIZE = 64 * 1024; // 64 KB static reusable buffer
const staticZeroChunk = new Uint8Array(UPLOAD_CHUNK_SIZE);

export async function measureUploadBandwidth(
  apiUrl: string,
  sizeMb: number = 2
): Promise<UploadBandwidthResult> {
  const endpoint = `${apiUrl.replace(/\/+$/, "")}/api/v1/network/speed-test/upload`;
  const totalBytes = sizeMb * 1024 * 1024;

  let sent = 0;
  const stream = new ReadableStream({
    pull(controller) {
      if (sent >= totalBytes) {
        controller.close();
        return;
      }
      const remaining = totalBytes - sent;
      if (remaining < UPLOAD_CHUNK_SIZE) {
        controller.enqueue(staticZeroChunk.subarray(0, remaining));
        sent += remaining;
      } else {
        controller.enqueue(staticZeroChunk);
        sent += UPLOAD_CHUNK_SIZE;
      }
    },
  });

  const startTime = performance.now();
  let response: Response;

  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Length": totalBytes.toString(),
      },
      body: stream,
      // @ts-ignore - duplex is required for streaming request bodies in Node fetch
      duplex: "half",
    });
  } catch (err: any) {
    throw new NetworkError(`Upload test failed: ${err.message}`);
  }

  if (!response.ok) {
    throw new BandwidthError(`Upload speed test failed with HTTP ${response.status}`, response.status);
  }

  const endTime = performance.now();
  const durationMs = Math.max(endTime - startTime, 1);
  const elapsedSeconds = durationMs / 1000;
  const bits = totalBytes * 8;
  const uploadMbps = Number((bits / elapsedSeconds / 1_000_000).toFixed(2));

  return {
    uploadMbps,
    bytes: totalBytes,
    durationMs: Math.round(durationMs),
    description: "Observed bandwidth to Clipper-X test server",
  };
}
