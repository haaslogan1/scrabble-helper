import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth-layout">
      <div className="auth-layout__hero">
        <h1>Scrabble Helper</h1>
        <p>Sign in to start games, track scores, and view your personal stats.</p>
      </div>
      {children}
    </div>
  );
}
