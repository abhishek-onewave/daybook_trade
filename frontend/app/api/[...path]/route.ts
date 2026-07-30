const HOP_BY_HOP_HEADERS = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "proxy-connection",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
];
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const DEMO_MODE = process.env.DAYBOOK_DEMO_MODE === "true";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function proxyHeaders(source: Headers) {
  const headers = new Headers(source);

  for (const name of headers.get("connection")?.split(",") ?? []) {
    headers.delete(name.trim());
  }
  for (const name of HOP_BY_HOP_HEADERS) {
    headers.delete(name);
  }
  headers.delete("host");

  return headers;
}

function gatewayConfig() {
  const configuredOrigin = process.env.DAYBOOK_API_ORIGIN?.trim();
  const token = process.env.DAYBOOK_API_TOKEN?.trim();

  if (
    IS_PRODUCTION &&
    (!configuredOrigin || (!DEMO_MODE && (!token || token.length < 32)))
  ) {
    throw new Error(
      "A secure DAYBOOK_API_ORIGIN and, outside demo mode, DAYBOOK_API_TOKEN are required in production.",
    );
  }

  const origin = new URL(configuredOrigin || "http://127.0.0.1:8000");
  if (!["http:", "https:"].includes(origin.protocol)) {
    throw new Error("DAYBOOK_API_ORIGIN must use http or https.");
  }
  if (IS_PRODUCTION && origin.protocol !== "https:") {
    throw new Error("DAYBOOK_API_ORIGIN must use https in production.");
  }

  return { origin: origin.origin, token };
}

function rejectCrossSiteMutation(request: Request) {
  if (SAFE_METHODS.has(request.method)) {
    return null;
  }

  const presentedOrigin = request.headers.get("origin");
  try {
    const requestUrl = new URL(request.url);
    const host = request.headers.get("host") || requestUrl.host;
    const forwardedProtocol = request.headers
      .get("x-forwarded-proto")
      ?.split(",", 1)[0]
      ?.trim()
      .toLowerCase();
    const protocol = forwardedProtocol || requestUrl.protocol.slice(0, -1);
    if (!["http", "https"].includes(protocol)) {
      throw new Error("invalid protocol");
    }
    const expectedOrigin = new URL(`${protocol}://${host}`).origin;
    if (!presentedOrigin || new URL(presentedOrigin).origin !== expectedOrigin) {
      throw new Error("origin mismatch");
    }
  } catch {
    return Response.json({ detail: "Cross-site request blocked." }, { status: 403 });
  }

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin") {
    return Response.json({ detail: "Cross-site request blocked." }, { status: 403 });
  }
  return null;
}

async function forward(request: Request) {
  const csrfRejection = rejectCrossSiteMutation(request);
  if (csrfRejection) {
    return csrfRejection;
  }

  let config: ReturnType<typeof gatewayConfig>;
  try {
    config = gatewayConfig();
  } catch (error) {
    console.error("Daybook API gateway is not configured.", error);
    return Response.json({ detail: "Service unavailable." }, { status: 503 });
  }

  const incoming = new URL(request.url);
  const target = new URL(`${incoming.pathname}${incoming.search}`, config.origin);
  const headers = proxyHeaders(request.headers);

  // Keep Web Basic Auth and the backend credential at separate trust boundaries.
  headers.delete("authorization");
  headers.delete("cookie");
  headers.delete("x-daybook-api-token");
  if (config.token) {
    headers.set("x-daybook-api-token", config.token);
  }

  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    redirect: "manual",
    signal: request.signal,
  };
  if (request.body && !["GET", "HEAD"].includes(request.method)) {
    init.body = request.body;
    init.duplex = "half";
  }

  try {
    const upstream = await fetch(target, init);
    const responseHeaders = proxyHeaders(upstream.headers);

    // Node fetch decodes compressed bodies before exposing the stream.
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");
    responseHeaders.delete("set-cookie");

    const location = responseHeaders.get("location");
    if (upstream.status >= 300 && upstream.status < 400 && location) {
      let redirectTarget: URL;
      try {
        redirectTarget = new URL(location, target);
      } catch {
        return Response.json(
          { detail: "Invalid API redirect." },
          { status: 502 },
        );
      }
      if (redirectTarget.origin !== config.origin) {
        return Response.json(
          { detail: "External API redirect blocked." },
          { status: 502 },
        );
      }
      responseHeaders.set(
        "location",
        `${redirectTarget.pathname}${redirectTarget.search}${redirectTarget.hash}`,
      );
    }

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Daybook API request failed.", error);
    return Response.json({ detail: "API unavailable." }, { status: 502 });
  }
}

export {
  forward as DELETE,
  forward as GET,
  forward as HEAD,
  forward as OPTIONS,
  forward as PATCH,
  forward as POST,
  forward as PUT,
};
