import { renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { useGameReturnTo } from "./useGameReturnTo";

function renderReturnTo(initialEntries: Parameters<typeof MemoryRouter>[0]["initialEntries"]) {
  return renderHook(() => useGameReturnTo(), {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    ),
  }).result.current;
}

describe("useGameReturnTo", () => {
  it("prefers location.state.returnTo", () => {
    const returnTo = renderReturnTo([
      {
        pathname: "/game/rules",
        search: "?gameId=99",
        state: { returnTo: "/game/42/play" },
      },
    ]);
    expect(returnTo).toBe("/game/42/play");
  });

  it("falls back to gameId query param", () => {
    const returnTo = renderReturnTo(["/game/rules?gameId=42"]);
    expect(returnTo).toBe("/game/42/play");
  });

  it("falls back to home when no game context", () => {
    const returnTo = renderReturnTo(["/game/rules"]);
    expect(returnTo).toBe("/");
  });
});
