"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginPanel } from "@/components/LoginPanel";

type AuthState = "checking" | "authenticated" | "unauthenticated";

const LOCAL_AUTH_KEY = "pm_local_auth";
const DEMO_USERNAME = "user";
const DEMO_PASSWORD = "password";

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>("checking");

  useEffect(() => {
    let isActive = true;

    const checkAuth = async () => {
      try {
        const response = await fetch("/api/auth/status");
        if (response.ok) {
          const data = await response.json();
          if (isActive) {
            setAuthState(
              data.authenticated ? "authenticated" : "unauthenticated"
            );
          }
          return;
        }

        if (response.status === 404 && isActive) {
          const localAuth = localStorage.getItem(LOCAL_AUTH_KEY) === "true";
          setAuthState(localAuth ? "authenticated" : "unauthenticated");
        }
      } catch {
        if (isActive) {
          const localAuth = localStorage.getItem(LOCAL_AUTH_KEY) === "true";
          setAuthState(localAuth ? "authenticated" : "unauthenticated");
        }
      }
    };

    checkAuth();

    return () => {
      isActive = false;
    };
  }, []);

  const handleLogin = async (username: string, password: string) => {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
      localStorage.removeItem(LOCAL_AUTH_KEY);
      setAuthState("authenticated");
      return null;
    }

    if (response.status === 404) {
      if (username === DEMO_USERNAME && password === DEMO_PASSWORD) {
        localStorage.setItem(LOCAL_AUTH_KEY, "true");
        setAuthState("authenticated");
        return null;
      }
    }

    return "Invalid username or password.";
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore network failures; local session will still be cleared.
    }
    localStorage.removeItem(LOCAL_AUTH_KEY);
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
      <KanbanBoard />
    </div>
  );
}
