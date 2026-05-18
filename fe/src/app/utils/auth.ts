// Token management with expiry (7 days)
const TOKEN_KEY = "admin_token";
const EXPIRY_KEY = "admin_token_expiry";
const TOKEN_EXPIRY_DAYS = 7;

export interface StoredToken {
  key: string;
  expiresAt: number; // timestamp in ms
}

export function saveToken(key: string): void {
  const expiresAt = Date.now() + TOKEN_EXPIRY_DAYS * 24 * 60 * 60 * 1000;
  localStorage.setItem(TOKEN_KEY, key);
  localStorage.setItem(EXPIRY_KEY, expiresAt.toString());
}

export function getToken(): string | null {
  const key = localStorage.getItem(TOKEN_KEY);
  const expiryStr = localStorage.getItem(EXPIRY_KEY);

  if (!key || !expiryStr) return null;

  const expiresAt = parseInt(expiryStr, 10);
  const now = Date.now();

  // Check if token expired
  if (now > expiresAt) {
    clearToken();
    return null;
  }

  return key;
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXPIRY_KEY);
}

export function getTokenExpiryDate(): Date | null {
  const expiryStr = localStorage.getItem(EXPIRY_KEY);
  if (!expiryStr) return null;
  return new Date(parseInt(expiryStr, 10));
}

export function isTokenValid(): boolean {
  return getToken() !== null;
}

export function getRemainingDays(): number {
  const expiryStr = localStorage.getItem(EXPIRY_KEY);
  if (!expiryStr) return 0;

  const expiresAt = parseInt(expiryStr, 10);
  const now = Date.now();
  const remainingMs = expiresAt - now;

  if (remainingMs <= 0) return 0;

  return Math.ceil(remainingMs / (24 * 60 * 60 * 1000));
}
