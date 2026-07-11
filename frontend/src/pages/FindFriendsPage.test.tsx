import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", () => ({
  listFriends: vi.fn().mockResolvedValue([
    {
      id: 1,
      username: "smtpsenderforlogan",
      name: "logan",
      avatar_url: "https://lh3.googleusercontent.com/a/example=s96-c",
    },
    {
      id: 2,
      username: "ccmitchellusa",
      name: "Chris Mitchell",
      avatar_url: null,
    },
  ]),
  listIncomingFriendRequests: vi.fn().mockResolvedValue([]),
  searchUsers: vi.fn(),
  sendFriendRequest: vi.fn(),
  acceptFriendRequest: vi.fn(),
  denyFriendRequest: vi.fn(),
  removeFriend: vi.fn(),
}));

import FindFriendsPage from "./FindFriendsPage";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/friends"]}>
      <FindFriendsPage />
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FindFriendsPage avatars", () => {
  it("uses friend-list__row__label on name spans and keeps Google img circular classes", async () => {
    const { container } = renderPage();

    await waitFor(() => {
      expect(screen.getByText(/@smtpsenderforlogan/)).toBeInTheDocument();
    });

    const labels = container.querySelectorAll(".friend-list__row__label");
    expect(labels.length).toBe(2);

    const googleImg = container.querySelector(
      'img.avatar.avatar--sm[src*="googleusercontent.com"]',
    );
    expect(googleImg).not.toBeNull();

    const initial = container.querySelector("span.avatar.avatar--sm");
    expect(initial).not.toBeNull();
    expect(initial).toHaveTextContent("C");
    expect(initial?.classList.contains("friend-list__row__label")).toBe(false);
  });
});
