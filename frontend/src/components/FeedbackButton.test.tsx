import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import FeedbackButton from "./FeedbackButton";

vi.mock("../api", () => ({
  submitFeedback: vi.fn().mockResolvedValue(undefined),
}));

import { submitFeedback } from "../api";

function renderFeedback(path = "/games") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <FeedbackButton />
    </MemoryRouter>,
  );
}

function openFeedbackModal() {
  const buttons = screen.getAllByRole("button", { name: "Send feedback" });
  return buttons[buttons.length - 1];
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FeedbackButton", () => {
  it("shows char counter starting at 0/2000", async () => {
    const user = userEvent.setup();
    renderFeedback();
    await user.click(openFeedbackModal());
    expect(screen.getByText("0/2000")).toBeInTheDocument();
  });

  it("hard stops at 2000 characters", async () => {
    const user = userEvent.setup();
    renderFeedback();
    await user.click(openFeedbackModal());
    const textarea = screen.getByPlaceholderText("Tell us what you think…") as HTMLTextAreaElement;
    const longText = "a".repeat(2001);
    await user.click(textarea);
    await user.paste(longText);
    expect(textarea.value.length).toBe(2000);
    expect(screen.getByText("2000/2000")).toBeInTheDocument();
  });

  it("submits feedback successfully", async () => {
    const user = userEvent.setup();
    renderFeedback("/game/42/play");
    await user.click(openFeedbackModal());
    await user.type(screen.getByPlaceholderText("Tell us what you think…"), "Nice app");
    await user.click(screen.getByRole("button", { name: "Submit" }));
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        message: "Nice app",
        category: undefined,
        page_url: "/game/42/play",
        game_id: 42,
      });
    });
    await waitFor(() => {
      expect(screen.getByText("Thanks — your feedback was sent.")).toBeInTheDocument();
    });
  });
});
