export class ClipperXError extends Error {
  public readonly code: string;
  public readonly statusCode?: number;

  constructor(message: string, code: string = "CLIPPER_X_ERROR", statusCode?: number) {
    super(message);
    this.name = "ClipperXError";
    this.code = code;
    this.statusCode = statusCode;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class AuthenticationError extends ClipperXError {
  constructor(message: string = "Authentication failed", statusCode: number = 401) {
    super(message, "AUTHENTICATION_ERROR", statusCode);
    this.name = "AuthenticationError";
  }
}

export class AuthorizationError extends ClipperXError {
  constructor(message: string = "Unauthorized node operation", statusCode: number = 403) {
    super(message, "AUTHORIZATION_ERROR", statusCode);
    this.name = "AuthorizationError";
  }
}

export class NetworkError extends ClipperXError {
  constructor(message: string, statusCode?: number) {
    super(message, "NETWORK_ERROR", statusCode);
    this.name = "NetworkError";
  }
}

export class RegistrationError extends ClipperXError {
  constructor(message: string, statusCode?: number) {
    super(message, "REGISTRATION_ERROR", statusCode);
    this.name = "RegistrationError";
  }
}

export class HeartbeatError extends ClipperXError {
  constructor(message: string, statusCode?: number) {
    super(message, "HEARTBEAT_ERROR", statusCode);
    this.name = "HeartbeatError";
  }
}

export class BandwidthError extends ClipperXError {
  constructor(message: string, statusCode?: number) {
    super(message, "BANDWIDTH_ERROR", statusCode);
    this.name = "BandwidthError";
  }
}
