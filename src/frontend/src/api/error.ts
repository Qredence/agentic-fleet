import { ApiRequestError, type ApiErrorDetails } from "./types";

export interface FormattedApiError {
  message: string;
  status?: number;
  code?: string;
  validationErrors?: string[];
}

function formatValidationErrors(
  details: ApiErrorDetails | undefined,
): string[] | undefined {
  if (!details?.validation_errors?.length) return undefined;
  return details.validation_errors.map((err) => `${err.field}: ${err.message}`);
}

export function formatApiError(error: unknown): FormattedApiError {
  if (error instanceof ApiRequestError) {
    return {
      message: error.message,
      status: error.status,
      code: error.code,
      validationErrors: formatValidationErrors(error.details),
    };
  }

  if (error instanceof Error) {
    return { message: error.message };
  }

  if (typeof error === "object" && error !== null) {
    const errorObj = error as {
      message?: string;
      detail?: string;
      error?: string;
    };
    return {
      message:
        errorObj.message ??
        errorObj.detail ??
        errorObj.error ??
        "Unknown error occurred"
    };
  }

  return { message: "Unknown error occurred" };
}
