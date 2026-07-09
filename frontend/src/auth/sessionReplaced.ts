const SESSION_REPLACED_KEY = "auth:session-replaced";

export function storeSessionReplacedMessage(message: string): void {
  sessionStorage.setItem(SESSION_REPLACED_KEY, message);
}

export function consumeSessionReplacedMessage(): string | null {
  const message = sessionStorage.getItem(SESSION_REPLACED_KEY);
  if (message) sessionStorage.removeItem(SESSION_REPLACED_KEY);
  return message;
}

export function sessionReplacedMessageFromDevice(
  device: "mobile" | "tablet" | "computer" | null | undefined,
): string {
  const label = device === "mobile" ? "mobile" : device === "tablet" ? "tablet" : "computer";
  return `A session already existed on ${label}. That session has been logged off.`;
}
