export class ApiError extends Error {
  constructor(detail, status) {
    super(detail);
    this.status = status;
  }
}

export async function api(path, options = {}) {
  const { body, ...rest } = options;
  const res = await fetch(path, {
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...rest,
  });
  if (!res.ok) {
    let detail = "Something went wrong — please try again.";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

export const money = (cents) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
