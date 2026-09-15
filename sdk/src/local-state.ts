import * as fs from "fs";
import * as path from "path";
import { NodeLocalState } from "./types";

/**
 * LocalStateManager handles local disk persistence of the node credential and identifier.
 *
 * NOTE: For V1 development, credentials are stored in a restricted local JSON file (mode 0600).
 * In production desktop/mobile environments, this should be backed by platform-native
 * secure enclaves (e.g., Linux Secret Service, macOS Keychain, or Windows DPAPI).
 */
export class LocalStateManager {
  private filePath: string;

  constructor(filePath?: string) {
    this.filePath = filePath || path.resolve(process.cwd(), ".clipper-x-state.json");
  }

  public getFilePath(): string {
    return this.filePath;
  }

  public loadState(): NodeLocalState | null {
    try {
      if (!fs.existsSync(this.filePath)) {
        return null;
      }
      const raw = fs.readFileSync(this.filePath, "utf-8");
      const parsed = JSON.parse(raw);
      if (parsed && parsed.nodeId && parsed.nodeToken) {
        return parsed as NodeLocalState;
      }
      return null;
    } catch {
      return null;
    }
  }

  public saveState(state: NodeLocalState): void {
    const dir = path.dirname(this.filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    const data = JSON.stringify(state, null, 2);
    // Write with restricted permissions (0600 - Owner Read/Write only)
    fs.writeFileSync(this.filePath, data, { mode: 0o600 });
  }

  public clearState(): void {
    try {
      if (fs.existsSync(this.filePath)) {
        fs.unlinkSync(this.filePath);
      }
    } catch {
      // Ignored if already removed
    }
  }
}
