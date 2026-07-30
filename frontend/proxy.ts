import { timingSafeEqual } from "node:crypto";

import { type NextRequest, NextResponse } from "next/server";

import { environmentFlag } from "@/lib/environment";

const USERNAME = "daybook";
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const DEMO_MODE = environmentFlag(process.env.DAYBOOK_DEMO_MODE);

function matches(expected: string, actual: string) {
  const expectedBytes = Buffer.from(expected);
  const actualBytes = Buffer.from(actual);

  return (
    expectedBytes.length === actualBytes.length &&
    timingSafeEqual(expectedBytes, actualBytes)
  );
}

function securityHeaders(response: NextResponse) {
  response.headers.set("Cache-Control", "private, no-store");
  if (IS_PRODUCTION) {
    response.headers.set(
      "Strict-Transport-Security",
      "max-age=63072000; includeSubDomains",
    );
  }
  return response;
}

export function proxy(request: NextRequest) {
  const password = process.env.DAYBOOK_ACCESS_PASSWORD;

  const forwardedProtocol = request.headers
    .get("x-forwarded-proto")
    ?.split(",", 1)[0]
    ?.trim()
    .toLowerCase();
  const usesHttps =
    request.nextUrl.protocol === "https:" || forwardedProtocol === "https";
  if (IS_PRODUCTION && !usesHttps) {
    return securityHeaders(
      new NextResponse("HTTPS is required.", { status: 426 }),
    );
  }

  if (IS_PRODUCTION && !DEMO_MODE && (!password || password.length < 16)) {
    console.error(
      "DAYBOOK_ACCESS_PASSWORD must be at least 16 characters in production.",
    );
    return securityHeaders(
      new NextResponse("Service unavailable.", { status: 503 }),
    );
  }
  if (!password) {
    return securityHeaders(NextResponse.next());
  }

  const authorization = request.headers.get("authorization");
  const presented = authorization?.match(/^Basic\s+(\S+)$/i)?.[1] ?? "";
  const expected = Buffer.from(`${USERNAME}:${password}`).toString("base64");

  if (matches(expected, presented)) {
    const downstreamHeaders = new Headers(request.headers);
    downstreamHeaders.delete("authorization");
    downstreamHeaders.delete("proxy-authorization");
    return securityHeaders(
      NextResponse.next({ request: { headers: downstreamHeaders } }),
    );
  }

  return securityHeaders(
    new NextResponse("Authentication required.", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="Daybook", charset="UTF-8"',
      },
    }),
  );
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
