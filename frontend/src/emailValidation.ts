export type EmailValidationResult = { ok: true; email: string } | { ok: false; message: string };

export function validateEmailInput(email: string): EmailValidationResult {
  const normalized = email.trim().toLowerCase();
  if (!normalized) {
    return { ok: false, message: "Email is required." };
  }
  if (normalized.length > 254) {
    return { ok: false, message: "Email is too long (max 254 characters)." };
  }
  if (!normalized.includes("@")) {
    return { ok: false, message: "Enter a valid email address (e.g. name@example.com)." };
  }
  const [local, domain] = normalized.split("@");
  if (!local || !domain) {
    return { ok: false, message: "Enter a valid email address (e.g. name@example.com)." };
  }
  if (local.startsWith(".") || local.endsWith(".") || normalized.includes("..")) {
    return { ok: false, message: "Email cannot contain consecutive dots or start/end with a dot." };
  }
  const emailPattern =
    /^[a-z0-9](?:[a-z0-9._%+-]{0,62}[a-z0-9])?@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,63}$/;
  if (!emailPattern.test(normalized)) {
    return {
      ok: false,
      message: "Enter a valid email address with a domain (e.g. name@example.com).",
    };
  }
  return { ok: true, email: normalized };
}
