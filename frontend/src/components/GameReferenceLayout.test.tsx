import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import GameReferenceLayout from "./GameReferenceLayout";

afterEach(() => {
  cleanup();
});

describe("GameReferenceLayout", () => {
  it("renders children and back link from gameId query", () => {
    render(
      <MemoryRouter initialEntries={["/game/rules?gameId=7"]}>
        <GameReferenceLayout title="Test title">
          <p>Body content</p>
        </GameReferenceLayout>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Test title" })).toBeInTheDocument();
    expect(screen.getByText("Body content")).toBeInTheDocument();
    const back = screen.getByRole("link", { name: "← Back to game" });
    expect(back).toHaveAttribute("href", "/game/7/play");
  });

  it("uses state.returnTo when provided", () => {
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/game/rules",
            state: { returnTo: "/game/3/play" },
          } as never,
        ]}
      >
        <GameReferenceLayout title="Ref">
          <span>Child</span>
        </GameReferenceLayout>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "← Back to game" })).toHaveAttribute(
      "href",
      "/game/3/play",
    );
  });
});
