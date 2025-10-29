import { buildApiUrl } from "../api-config";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  parseJson?: boolean;
}

const parseResponse = async (response: Response) => {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch (error) {
    throw new ApiError("Failed to parse JSON response", response.status, { raw: text });
  }
};

export async function apiRequest<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = buildApiUrl(path);
  const { headers, parseJson = true, ...init } = options;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...headers,
    },
    ...init,
  });

  if (!response.ok) {
    const body = await parseResponse(response).catch(() => null);
    throw new ApiError(response.statusText || "API request failed", response.status, body ?? undefined);
  }

  if (!parseJson) {
    return undefined as T;
  }

  const body = await parseResponse(response);
  return body as T;
}
