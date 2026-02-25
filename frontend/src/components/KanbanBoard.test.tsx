import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";
import { vi } from "vitest";

const mockFetch = vi.fn();

const mockJsonResponse = (payload: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  );

beforeEach(() => {
  mockFetch.mockImplementation((input: RequestInfo, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.url;
    if (!init || init.method === "GET") {
      return mockJsonResponse(initialData);
    }

    if (init.method === "POST" && url.includes("/api/ai/board")) {
      const aiBoard = {
        ...initialData,
        cards: {
          ...initialData.cards,
          "card-1": {
            ...initialData.cards["card-1"],
            title: "AI updated title",
          },
        },
      };
      return mockJsonResponse({
        schemaVersion: 1,
        board: aiBoard,
        operations: [
          {
            type: "update_card",
            cardId: "card-1",
            title: "AI updated title",
            details: aiBoard.cards["card-1"].details,
          },
        ],
      });
    }

    if (init.method === "PUT" && typeof init.body === "string") {
      return mockJsonResponse(JSON.parse(init.body));
    }

    return mockJsonResponse(initialData);
  });
  global.fetch = mockFetch as unknown as typeof fetch;
});

describe("KanbanBoard", () => {
  it("renders five columns", async () => {
    render(<KanbanBoard />);
    const columns = await screen.findAllByTestId(/column-/i);
    expect(columns).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = await screen.findAllByTestId(/column-/i).then(
      (columns) => columns[0]
    );
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = await screen.findAllByTestId(/column-/i).then(
      (columns) => columns[0]
    );
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("sends an AI prompt and applies updates", async () => {
    render(<KanbanBoard />);

    await screen.findAllByTestId(/column-/i);

    await userEvent.type(
      screen.getByLabelText(/ask the ai/i),
      "Update card-1"
    );
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByText(/applied 1 update/i)
    ).toBeInTheDocument();
    expect(await screen.findByText("AI updated title")).toBeInTheDocument();
  });
});
