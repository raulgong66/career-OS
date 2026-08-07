function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function extractErrorDetail(body: unknown): string | null {
  if (!isRecord(body)) return null;
  if (typeof body.detail === 'string' && body.detail) return body.detail;
  if (isRecord(body.detail)) {
    if (typeof body.detail.detail === 'string' && body.detail.detail) {
      return body.detail.detail;
    }
  }
  if (typeof body.error === 'string' && body.error) return body.error;
  return null;
}

async function readBodyText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return '';
  }
}

function parseJsonText<T>(url: string, body: string): T {
  if (!body) {
    console.error(`[${url}] Empty response body`);
    throw new Error('Empty response from server.');
  }
  try {
    return JSON.parse(body) as T;
  } catch {
    console.error(`[${url}] Non-JSON response body:`, body);
    throw new Error('Invalid response from server (expected JSON).');
  }
}

function createHttpError(response: Response, body: string, fallback: string): Error {
  const status = response.status;
  let message = '';
  if (body.trim()) {
    try {
      message = extractErrorDetail(JSON.parse(body)) ?? '';
    } catch {
      message = body.trim();
    }
  }
  if (!message) message = fallback;
  console.error(`[${response.url}] HTTP ${status} ${response.statusText}`, body || '(empty body)');
  return new Error(`${message} (HTTP ${status})`);
}

export async function fetchJson<T>(
  url: string,
  init: RequestInit | undefined,
  fallbackMessage: string,
): Promise<T> {
  const response = await fetch(url, init);
  const body = await readBodyText(response);
  if (!response.ok) throw createHttpError(response, body, fallbackMessage);
  return parseJsonText<T>(url, body);
}

export async function fetchText(
  url: string,
  init: RequestInit | undefined,
  fallbackMessage: string,
): Promise<string> {
  const response = await fetch(url, init);
  const body = await readBodyText(response);
  if (!response.ok) throw createHttpError(response, body, fallbackMessage);
  return body;
}

export async function fetchBlob(
  url: string,
  init: RequestInit | undefined,
  fallbackMessage: string,
): Promise<Blob> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await readBodyText(response);
    throw createHttpError(response, body, fallbackMessage);
  }
  return response.blob();
}
