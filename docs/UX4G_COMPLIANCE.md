# UX4G Design System Compliance & Component Architecture

**Product:** EduTrace  
**Design System:** UX4G Design System 3.0 (`ux4g-web-components@3.0.2`)  
**Standard:** WCAG 2.1 AA / GIGW 3.0 Alignment  
**Status:** In Progress (R03 Component Layer Complete)

---

## 1. Overview & Architectural Contract

EduTrace is built strictly on the **UX4G Design System 3.0** (`ux4g-web-components@3.0.2`). All visual styling, interactive behaviors, typography, spacing, and color palettes originate from UX4G primitives and semantic CSS custom properties.

Per REBRAND_TASKS.md Decision 3, a thin, typed React wrapper layer is established in `frontend/src/components/ux4g/` exposing semantic components. The application consumes UI primitives exclusively through these wrappers.

A dedicated living component catalog and state showcase is maintained at `/dev/components` to visually and interactively verify all component states (default, hover, active, focus, disabled, error, and loading).

---

## 2. Foundations Verification

| Foundation | Specification | Implementation in EduTrace | Compliance Status |
|---|---|---|---|
| **Color Tokens** | 3-tier token architecture (Primitives → Semantics → Roles) | Centralized in `frontend/src/styles/tokens.css` strictly aliasing `--ux4g-*` variables. Zero raw hex or rgb values outside tokens.css. Progressive linter (`scripts/lint-tokens.mjs`) enforces zero raw colors. | ✅ Verified |
| **Typography** | Noto Sans (Latin + Devanagari 400, 500, 600, 700) | Bundled offline via `@fontsource/noto-sans` and `@fontsource/noto-sans-devanagari` with `system-ui` fallback. | ✅ Verified |
| **Spacing & Grid** | 4px non-linear spacing scale (`space-none` to `space-14`), 4-column mobile to 12-column desktop | Tailwind 4px spacing scale mapped to `--ux4g-space-*` variables; default Tailwind color palette completely disabled. | ✅ Verified |
| **Iconography** | Material Symbols / Material Design Icons | Embedded `UX4G Material Icons` and `UX4G Material Icons Outlined` font families bundled in `ux4g.css` with `.ux4g-icon` classes. | ✅ Verified |
| **Accessibility** | WCAG 2.1 AA standard | Visible focus rings on all interactive elements, keyboard accessibility on all custom controls, semantic landmarks (`header`, `nav`, `main`, `aside`, `footer`), explicit error summaries with focus routing. | ✅ Verified |
| **Footer** | Demo disclaimer + secondary links | Prototype disclaimer banner ("Demo mode: APAAR registry is simulated") and copyright strip. No misuse of National Emblem or official logos. | ✅ Verified |

---

## 3. Component Coverage Inventory (28 Wrappers)

### 3.1 Core Components
1. **Button** (`Button.tsx`): Adheres strictly to Design.md §2 & §12 with mandatory base class + variant class + size class composition (`ux4g-btn ux4g-btn-primary ux4g-btn-m`). Variants: primary, outline-primary, tonal-primary, text-primary, danger, outline-danger, text-danger, outline-neutral, text-neutral. Includes loading state with spinner and `aria-busy`.
2. **IconButton** (`Button.tsx`): Standalone icon button with base `ux4g-icon-btn` and required `aria-label`.
3. **Link** (`Link.tsx`): Text links (`ux4g-text-link-sm`, `ux4g-text-link-md`) with React Router integration and external security attributes (`rel="noopener noreferrer"`).
4. **Icon** (`Icon.tsx`): Embedded Material Symbols icons wrapper (`ux4g-icon ux4g-icon-outlined`) with color modifiers and accessible label support.
5. **Badge** (`Badge.tsx`): Standard badge (`ux4g-badge ux4g-badge-{type}-{color}`).
6. **FlagBadge** (`Badge.tsx`): Implementation of SPEC §19 and DECISIONS.md Difference 6:
   - Error: Red filled (`--edutrace-flag-error-bg`)
   - Exception: Red outlined (`--edutrace-flag-exception-border`)
   - Warning: Orange (`--edutrace-flag-warning-bg`)
   - Info: Neutral grey (`--edutrace-flag-info-bg`)
7. **RoleBadge** (`Badge.tsx`): Human-readable badges for system roles (`college_admin`, `aicte_officer`, `verifier`, etc.).
8. **Tag** (`Tag.tsx`): Interactive tags (`ux4g-tag ux4g-tag-{variant}-{color}`) with dismiss action.
9. **Alert** (`Alert.tsx`): Notifications (`ux4g-alert ux4g-alert-{variant}`) with accessible `role="alert"` / `role="status"` and dismiss action.
10. **Toast** (`Toast.tsx`, `ToastContext.tsx`): Dynamic toasts with auto-dismiss timers and `aria-live="polite"` viewport.
11. **Tooltip** (`Tooltip.tsx`): Tooltip bubbles (`ux4g-tooltip ux4g-tooltip-{placement}`) with keyboard and mouse triggers and `aria-describedby`.

### 3.2 Form Components
12. **Input** (`Input.tsx`): Text input within `.ux4g-input ux4g-input-{size} ux4g-input-{state}` with leading/trailing icon slots and `aria-invalid`.
13. **Textarea** (`Textarea.tsx`): Multi-line text field (`.ux4g-textarea`) with configurable rows.
14. **Select** (`Select.tsx`): Styled select dropdown (`.ux4g-input` container with arrow indicator).
15. **Radio** (`Radio.tsx`): Accessible radio input (`.ux4g-radio ux4g-radio-{size}`).
16. **Checkbox** (`Checkbox.tsx`): Accessible checkbox (`.ux4g-checkbox ux4g-checkbox-{size}`) with indeterminate state support.
17. **Switch** (`Switch.tsx`): Boolean switch toggle (`.ux4g-switch`) with `role="switch"`.
18. **DatePicker** (`DatePicker.tsx`): ISO date input (YYYY-MM-DD) with calendar icon.
19. **FileUpload** (`FileUpload.tsx`): Drag-and-drop file upload dropzone with keyboard browse, format validation, and file details preview.
20. **OtpInput** (`OtpInput.tsx`): 6-box discrete digit input with keyboard auto-advance, backspace retreat, and full-code clipboard paste.
21. **FormField** (`FormField.tsx`): Form field container binding label, required indicator, hint text, and error alert via `aria-describedby` and `aria-invalid`.
22. **ErrorSummary** (`ErrorSummary.tsx`): Form error banner at top of page auto-focusing on submit error, with clickable links focusing invalid inputs.

### 3.3 Navigation Components
23. **Navbar** (`Navbar.tsx`): Header navigation (`.ux4g-navbar`, `.ux4g-navbar-wrap`, `.ux4g-navbar-logo`, `.ux4g-navbar-links`).
24. **Sidebar** (`Sidebar.tsx`): Semantic navigation landmark (`<aside role="navigation">`) with section groupings and active route indicators.
25. **Breadcrumb** (`Breadcrumb.tsx`): Breadcrumb trails (`.ux4g-breadcrumb`) with `aria-current="page"`.
26. **Tabs** (`Tabs.tsx`): Tabbed navigation (`.ux4g-tab ux4g-tab-underline`) with full ARIA roles (`tablist`, `tab`, `tabpanel`) and ArrowLeft/ArrowRight keyboard navigation.
27. **Stepper** (`Stepper.tsx`): Multi-step progress tracker (`.ux4g-stepper ux4g-stepper-horizontal`) with completed checkmarks and `aria-current="step"`.
28. **Pagination** (`Pagination.tsx`): Accessible pagination bar (`.ux4g-pagination-wrapper`) with next/previous controls, page numbers, and ellipsis.
29. **Footer** (`Footer.tsx`): Official footer wrapper (`.ux4g-footer-wrapper ux4g-footer-primary`) with prototype notice banner and secondary legal links.

### 3.4 Content Components
30. **Card** (`Card.tsx`): Bounded surface container (`.ux4g-card ux4g-card-solid`) with header, title, body, and footer sub-components.
31. **Accordion** (`Accordion.tsx`): Collapsible accordion panels (`.ux4g-accordion ux4g-accordion-arrow-right`) with `aria-expanded` and keyboard toggle.
32. **Modal** (`Modal.tsx`): Accessible dialog box (`.ux4g-modal-box ux4g-modal-m`) with backdrop, focus trapping, Escape key dismiss, and `role="dialog"`.
33. **Table** (`Table.tsx`): Data table (`.ux4g-table ux4g-table-m ux4g-table-column-dividers ux4g-table-zebra-rows`) with header sorting indicators (`aria-sort`) and caption.
34. **EmptyState** (`EmptyState.tsx`): Empty state placeholder card with graphic, heading, description, and action button.
35. **Spinner** (`Spinner.tsx`): Loading indicator (`.ux4g-spinner-primary-full`) with `role="status"` and screen reader text.
36. **Skeleton** (`Skeleton.tsx`): Placeholder loading skeleton with shimmer animation.
37. **Progress** (`Progress.tsx`): Progress bar with `role="progressbar"`, aria bounds, and percentage tracking.

---

## 4. Gaps and Architectural Resolutions

| Gap Description | UX4G Web Package Status | Architectural Resolution in EduTrace |
|---|---|---|
| **Toast Component** | Shipped in Flutter UX4G (`ux4g_flutter_components`), but absent in `ux4g-web-components` CSS. | Composed custom `Toast` and `ToastProvider` using UX4G Alert primitives (`ux4g-alert`), UX4G elevation shadow (`ux4g-shadow-l3`), and accessible `aria-live="polite"` region. |
| **Data Grid / Virtualization** | UX4G includes `.ux4g-table` CSS classes, but does not provide JavaScript virtualization for 5,000+ row datasets. | Composed table wrappers using official `.ux4g-table` classes integrated with TanStack Table for efficient virtualization. |
| **Skeleton Placeholder** | UX4G includes spinner but no animated skeleton block. | Composed `Skeleton` using UX4G border radius (`--ux4g-radius-md`) and neutral subtle background token (`--ux4g-bg-neutral-subtle`) with pulse animation. |
| **Info Flag Semantic Mapping** | UX4G defines Info token ramp in cyan (`#006D75`), but SPEC.md §19 mandates neutral grey for Info flags in audit contexts. | Aliased `--edutrace-flag-info-*` to UX4G Neutral tokens (`--ux4g-color-neutral-600`, `--ux4g-color-neutral-100`) while Error, Exception, and Warning map directly to UX4G Red and Orange. |

---

## 5. Automated Verification

- **Linting:** `npm run lint` enforces zero raw hex, zero raw rgb, and zero Tailwind color classes outside `tokens.css`.
- **Unit Testing:** 100% of the 28 wrappers are tested across 4 dedicated test suites (`CoreComponents.test.tsx`, `FormComponents.test.tsx`, `NavigationComponents.test.tsx`, `ContentComponents.test.tsx`, `DevComponentsPage.test.tsx`) asserting DOM rendering, keyboard interaction, and accessible naming.
- **Showcase Catalog:** Accessible live at `/dev/components` displaying all components in default, hover, focus, disabled, error, and loading states.
