import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import DictionaryPage from "./DictionaryPage";

vi.mock("../api", () => ({
  checkDictionaryWord: vi.fn(),
}));

import { checkDictionaryWord } from "../api";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DictionaryPage", () => {
  it("shows challenge-only callout", () => {
    render(
      <MemoryRouter initialEntries={["/game/dictionary?gameId=1"]}>
        <DictionaryPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Challenge lookup only/i)).toBeInTheDocument();
    expect(screen.getByText(/during your turn/i)).toBeInTheDocument();
  });

  it("shows error when submitting empty word", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/game/dictionary"]}>
        <DictionaryPage />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: "Check word" }));
    expect(screen.getByText(/Enter the word exactly as played/i)).toBeInTheDocument();
    expect(checkDictionaryWord).not.toHaveBeenCalled();
  });

  it("shows valid result from API", async () => {
    vi.mocked(checkDictionaryWord).mockResolvedValue({ word: "QUIZ", valid: true });
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/game/dictionary"]}>
        <DictionaryPage />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText("Word as played"), "QUIZ");
    await user.click(screen.getByRole("button", { name: "Check word" }));
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("QUIZ is valid.");
    });
  });

  it("shows invalid result from API", async () => {
    vi.mocked(checkDictionaryWord).mockResolvedValue({ word: "NOTAWORD", valid: false });
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/game/dictionary"]}>
        <DictionaryPage />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText("Word as played"), "NOTAWORD");
    await user.click(screen.getByRole("button", { name: "Check word" }));
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("NOTAWORD is not in the dictionary.");
    });
  });
});
