"use client";

import { useEffect, useState } from "react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginPanel } from "@/components/LoginPanel";

type AuthState = "checking" | "authenticated" | "unauthenticated";

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>("checking");

  useEffect(() => {
    let isActive = true;

    const checkAuth = async () => {
      try {
        const response = await fetch("/api/auth/status");
        if (isActive) {
          setAuthState(
            response.ok && (await response.json()).authenticated
              ? "authenticated"
              : "unauthenticated"
          );
        }
      } catch {
        if (isActive) {
          setAuthState("unauthenticated");
        }
      }
    };

    checkAuth();

    return () => {
      isActive = false;
    };
  }, []);

  const handleLogin = async (username: string, password: string) => {
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        setAuthState("authenticated");
        return null;
      }

      if (response.status === 401) {
        return "Invalid username or password.";
      }

      return "Unable to reach the server. Please try again.";
    } catch {
      return "Unable to reach the server. Please try again.";
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore network failures; cookie will have been cleared by the server already.
    }
    setAuthState("unauthenticated");
  };

  if (authState === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm font-semibold text-[var(--gray-text)]">
        Checking session...
      </div>
    );
  }

  if (authState === "unauthenticated") {
    return <LoginPanel onLogin={handleLogin} />;
  }

  return (
    <div className="relative">
      <div className="absolute right-6 top-6 z-10">
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] shadow-[var(--shadow)] transition hover:text-[var(--navy-dark)]"
        >
          Log out
        </button>
      </div>
      <ErrorBoundary>
        <KanbanBoard />
      </ErrorBoundary>
    </div>
  );
}
