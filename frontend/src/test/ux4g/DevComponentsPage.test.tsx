
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DevComponentsPage } from "../../pages/DevComponentsPage";

describe("DevComponentsPage", () => {
  it("renders all showcase sections with all states", () => {
    render(
      <MemoryRouter>
        <DevComponentsPage />
      </MemoryRouter>
    );

    // Header & page title
    expect(screen.getByText("UX4G Component Showcase & State Catalog")).toBeInTheDocument();
    expect(screen.getByText("Dev Only")).toBeInTheDocument();

    // Section 1: Buttons
    expect(screen.getByText("1. Core: Button & Icon Button")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Primary Button" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Disabled State" })).toBeDisabled();

    // Section 2: Links & Icons
    expect(screen.getByText("2. Core: Link & Material Symbols Icon")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Router Link (Default)" })).toBeInTheDocument();

    // Section 3: Badges, FlagBadge & Tags
    expect(screen.getByText("3. Core: Badges, FlagBadge (SPEC §19) & Tags")).toBeInTheDocument();
    expect(screen.getAllByTestId("flag-badge-error").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("flag-badge-exception").length).toBeGreaterThanOrEqual(1);

    // Section 4: Alerts & Toasts
    expect(screen.getByText("4. Core: Alerts, Toasts & Tooltips")).toBeInTheDocument();
    expect(screen.getByText("Trigger Sample Toast")).toBeInTheDocument();

    // Section 5: Forms
    expect(screen.getByText("5. Forms: FormField, ErrorSummary, Inputs & Controls")).toBeInTheDocument();
    expect(screen.getAllByRole("alert").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByPlaceholderText("e.g. Ramesh Kumar")).toBeInTheDocument();

    // Section 6: Navigation
    expect(screen.getByText("6. Navigation: Breadcrumbs, Tabs, Stepper & Pagination")).toBeInTheDocument();
    expect(screen.getByText("Lookup Institution")).toBeInTheDocument();

    // Section 7: Content
    expect(screen.getByText("7. Content: Card, Accordion, Modal, Table, EmptyState & Progress")).toBeInTheDocument();
    expect(screen.getAllByRole("table").length).toBeGreaterThanOrEqual(1);
  });
});
