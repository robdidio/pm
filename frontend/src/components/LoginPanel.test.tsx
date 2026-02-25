import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginPanel } from "@/components/LoginPanel";

describe("LoginPanel", () => {
  it("submits credentials to the login handler", async () => {
    const onLogin = vi.fn(async () => null);
    render(<LoginPanel onLogin={onLogin} />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(onLogin).toHaveBeenCalledWith("user", "password");
  });

  it("shows an error message when login fails", async () => {
    const onLogin = vi.fn(async () => "Invalid username or password.");
    render(<LoginPanel onLogin={onLogin} />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText(/invalid username or password/i)
    ).toBeInTheDocument();
  });
});
