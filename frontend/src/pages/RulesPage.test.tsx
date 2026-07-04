import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SCRABBLE_RULES } from "../content/rulesContent";
import RulesPage from "./RulesPage";

describe("RulesPage", () => {
  it("renders every section title", () => {
    render(
      <MemoryRouter initialEntries={["/game/rules?gameId=5"]}>
        <RulesPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Scrabble basics" })).toBeInTheDocument();
    for (const section of SCRABBLE_RULES) {
      expect(screen.getByRole("heading", { name: section.title })).toBeInTheDocument();
    }
  });

  it("links back to the live game", () => {
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/game/rules",
            search: "?gameId=5",
            state: { returnTo: "/game/5/play" },
          } as never,
        ]}
      >
        <RulesPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "← Back to game" })).toHaveAttribute(
      "href",
      "/game/5/play",
    );
  });

  it("includes official Hasbro rules link", () => {
    render(
      <MemoryRouter initialEntries={["/game/rules"]}>
        <RulesPage />
      </MemoryRouter>,
    );

    const official = screen.getByRole("link", { name: "Official rules (Hasbro)" });
    expect(official).toHaveAttribute("href", "https://scrabble.hasbro.com/en-us/rules");
    expect(official).toHaveAttribute("target", "_blank");
  });
});
