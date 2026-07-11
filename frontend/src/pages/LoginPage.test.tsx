import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    refresh: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn(),
  }),
}));

vi.mock("../api", () => ({
  getAuthConfig: vi.fn().mockResolvedValue({
    google_login_enabled: false,
    dev_login_enabled: false,
    local_auth_enabled: true,
    email_verification_enabled: true,
  }),
  login: vi.fn(),
  sendRegistrationCode: vi.fn(),
  verifyRegistration: vi.fn(),
  requestPasswordReset: vi.fn().mockResolvedValue({
    message: "If an account with that email can reset its password, we sent a 6-digit code.",
    expires_in_minutes: 15,
  }),
  confirmPasswordReset: vi.fn().mockResolvedValue(undefined),
}));

import {
  confirmPasswordReset,
  getAuthConfig,
  requestPasswordReset,
} from "../api";
import LoginPage from "./LoginPage";

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <LoginPage />
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(getAuthConfig).mockResolvedValue({
    google_login_enabled: false,
    dev_login_enabled: false,
    local_auth_enabled: true,
    email_verification_enabled: true,
  });
});

describe("LoginPage forgot password", () => {
  it("shows Forgot password link when local auth is enabled", async () => {
    renderLogin();
    expect(await screen.findByRole("button", { name: "Forgot password?" })).toBeInTheDocument();
  });

  it("requests a reset code and advances to confirm step", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(await screen.findByRole("button", { name: "Forgot password?" }));
    await user.type(screen.getByPlaceholderText("Email"), "reset@test.local");
    await user.click(screen.getByRole("button", { name: "Send reset code" }));

    await waitFor(() => {
      expect(requestPasswordReset).toHaveBeenCalledWith("reset@test.local");
    });
    expect(
      await screen.findByText(/if an account with that email can reset/i),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText("6-digit reset code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset password" })).toBeInTheDocument();
  });

  it("confirms reset and returns to sign in with success message", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(await screen.findByRole("button", { name: "Forgot password?" }));
    await user.type(screen.getByPlaceholderText("Email"), "reset@test.local");
    await user.click(screen.getByRole("button", { name: "Send reset code" }));
    await screen.findByPlaceholderText("6-digit reset code");

    await user.type(screen.getByPlaceholderText("6-digit reset code"), "123456");
    await user.type(
      screen.getByPlaceholderText("New password (10+ chars, letter and digit)"),
      "BrandNewPass1",
    );
    await user.type(screen.getByPlaceholderText("Confirm new password"), "BrandNewPass1");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(confirmPasswordReset).toHaveBeenCalledWith(
        "reset@test.local",
        "123456",
        "BrandNewPass1",
      );
    });
    expect(
      await screen.findByText(/password updated\. sign in with your new password/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Forgot password?" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
  });

  it("rejects mismatched confirm password without calling API", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(await screen.findByRole("button", { name: "Forgot password?" }));
    await user.type(screen.getByPlaceholderText("Email"), "reset@test.local");
    await user.click(screen.getByRole("button", { name: "Send reset code" }));
    await screen.findByPlaceholderText("6-digit reset code");

    await user.type(screen.getByPlaceholderText("6-digit reset code"), "123456");
    await user.type(
      screen.getByPlaceholderText("New password (10+ chars, letter and digit)"),
      "BrandNewPass1",
    );
    await user.type(screen.getByPlaceholderText("Confirm new password"), "DifferentPass1");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(confirmPasswordReset).not.toHaveBeenCalled();
  });
});
