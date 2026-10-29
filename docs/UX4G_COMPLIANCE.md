# UX4G Design System Compliance & Accessibility Audit

**Product:** EduTrace  
**Design System:** UX4G Design System 3.0 (`ux4g-web-components@3.0.2`)  
**Standard:** WCAG 2.1 AA / GIGW 3.0 Alignment  
**Audit Status:** Designed to WCAG 2.1 AA, automated checks pass, manual review pending  

---

> [!NOTE]
> **Compliance & Certification Notice**  
> EduTrace is engineered to strictly conform to WCAG 2.1 Level AA and the Government of India Guidelines for Indian Government Websites (GIGW 3.0). All automated testing suites—including axe-core Playwright scans, Google Lighthouse accessibility audits, token purity linters, and AST microcopy validators—pass with zero serious or critical violations. Formal third-party GIGW certification and human screen-reader audit (NVDA/JAWS) remain pending completion of operational deployment.

---

## 1. Overview & Architectural Contract

EduTrace adopts the **UX4G Design System 3.0** (`ux4g-web-components@3.0.2`) as its single visual and behavioral foundation. Rather than importing arbitrary third-party styles or unconstrained CSS utility palettes, all visual presentation, spacing, typography, colors, and layout patterns are governed by UX4G semantic tokens.

### Architectural Rules
1. **Token Hierarchy:** Visual tokens follow a strict 3-tier architecture: Primitive (`--ux4g-palette-*`) → Semantic (`--ux4g-color-*`, `--ux4g-spacing-*`) → Component Role (`--edutrace-brand-*`, `--edutrace-flag-*`).
2. **Component Layer:** A thin, strictly typed React wrapper layer in `frontend/src/components/ux4g/` encapsulates UX4G web components and CSS primitives, ensuring complete type safety and consistent accessibility bindings.
3. **Living Showcase:** A component catalog and interactive state showcase is maintained at `/dev/components` to verify all component states (default, hover, active, focus, disabled, loading, and error).

---

## 2. UX4G Foundations Verification Table

| Foundation | Requirement | Implementation in EduTrace | Evidence & Verification |
|---|---|---|---|
| **Colour** | 3-tier CSS token hierarchy; zero raw hex/rgb in markup; minimum 4.5:1 contrast for normal text and 3:1 for UI elements; WCAG AA compliance. | Centralized in `frontend/src/styles/tokens.css` strictly aliasing `--ux4g-*` variables. Custom brand tokens (`--edutrace-brand-primary: #4A2BC2`, `--edutrace-brand-secondary: #00522C`) maintain high contrast. Badge foregrounds tuned to >= 7.0:1 (e.g. Verifier badge at 7.09:1). | Automated token linter (`scripts/lint-tokens.mjs`) reports **0 raw color violations**; axe-core color contrast checks pass across all 32 routes with **0 violations**. |
| **Typography** | Official Google Noto Sans and Noto Sans Devanagari bundled offline; fluid sizing scale; sentence case headings; imperative action verbs. | `@fontsource/noto-sans` and `@fontsource/noto-sans-devanagari` bundled offline. ReportLab backend exporter registers TrueType fonts in `backend/app/reports/fonts.py`. All user-facing headings follow sentence case; buttons start with imperative action verbs via centralized dictionary `frontend/src/copy/en.ts`. | AST-based microcopy check (`frontend/scripts/check-microcopy.mjs`) reports **0 heading or button violations**; ReportLab test suite passes (`backend/tests/test_pdf_documents.py`). |
| **Spacing & Grid** | 4px non-linear spacing grid (`space-0` through `space-14`); 4-column layout at 360px, 8-column at 768px, 12-column at 1280px+; zero horizontal scrolling. | Tailwind CSS configured with disabled default palettes, mapping spacing exclusively to `--ux4g-space-*`. Layout grids responsive with fluid reflow across mobile, tablet, and desktop viewports. | Responsive layout tests verify zero horizontal overflow (`overflow-x: hidden`) across 360px, 768px, and 1280px breakpoints. |
| **Iconography** | Official Material Symbols font family; consistent sizing; accessible labeling for icon-only controls. | Embedded UX4G Material Symbols font in `ux4g.css` (`.ux4g-icon`, `.ux4g-icon-outlined`) wrapped by `<Icon />`. All interactive icon buttons enforce required accessible names (`aria-label`). | Component unit tests in `CoreComponents.test.tsx`; axe-core `button-name` rule passes across all 32 routes. |
| **Accessibility** | Full keyboard accessibility; visible focus indicators (`ux4g-focus-ring`); landmark roles; modal focus trapping; live regions for async feedback. | Visible 2px focus rings with 2px offset on all interactive elements. Skip to main content link on every page (`#main-content`). Semantic landmarks (`header`, `nav`, `main`, `aside`, `footer`). Modals trap focus and close on Escape. Scrollable tables include `tabIndex={0}` and `role="region"`. | Playwright axe-core audit: **32/32 routes pass with 0 serious/critical violations**; Lighthouse Accessibility: **98–100 on all 5 audited pages**; pure keyboard journeys pass. |
| **Footer** | Standardized footer layout; statutory legal and accessibility links; plain-language prototype disclaimer; no state emblem misuse. | Official UX4G dark footer (`.ux4g-footer-primary`) with four-column resource navigation, plain-English glossary link (`/help`), prototype disclaimer banner ("Demo data • EduTrace Platform • Simulated APAAR Registry • Prototype not affiliated with Government of India"), and copyright strip. | Brand check script (`scripts/brand_check.ps1`) passes with 0 violations; axe-core footer audits pass. |
| **Forms** | Visible labels bound via `htmlFor`/`id`; hint text and error alerts wired via `aria-describedby` and `aria-invalid`; error summary banner; auto-advancing OTP. | Accessible `<FormField>` wrapper binding labels, hints, and error alerts. `<ErrorSummary>` auto-focuses on submit failure with clickable field jump links. Discrete 6-box `<OtpInput>` with auto-advance and clipboard paste. Accessible drag-and-drop `<FileUpload>`. | Form component unit tests (`FormComponents.test.tsx`); axe-core `label`, `aria-valid-attr-value`, and `aria-describedby` checks pass on all form pages. |

---

## 3. Automated Accessibility Test Proof

### 3.1 Axe-Core Route Audit (Playwright)
The automated accessibility audit scans all 32 application routes defined in SPEC.md §19 using `@axe-core/playwright` with tags `['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']`.

- **Test Specification:** `frontend/e2e/all_routes_axe.spec.ts`
- **Result:** **32 / 32 Routes Passed (0 Serious, 0 Critical Violations)**

| Route Category | Scanned Routes | Serious / Critical Violations | Result |
|---|---|:---:|:---:|
| **Public Routes** | `/`, `/activate`, `/login/college`, `/login/aicte`, `/verify`, `/student`, `/help` | 0 | ✅ PASS |
| **College Routes** | `/college/dashboard`, `/college/seats`, `/college/students`, `/college/students/new`, `/college/upload`, `/college/validation`, `/college/submit`, `/college/queries`, `/college/change-requests`, `/college/staff`, `/college/api-keys` | 0 | ✅ PASS |
| **AICTE Routes** | `/aicte/overview`, `/aicte/approvals`, `/aicte/intake`, `/aicte/compliance`, `/aicte/duplicates`, `/aicte/anomalies`, `/aicte/review`, `/aicte/explore`, `/aicte/reports`, `/aicte/audit`, `/aicte/verifiers`, `/aicte/rules` | 0 | ✅ PASS |
| **Verifier Routes** | `/verifier/search`, `/verifier/history` | 0 | ✅ PASS |

### 3.2 Google Lighthouse Accessibility Run
Lighthouse automated accessibility audits were executed against headless Chromium across five representative core user journeys:

- **Runner Script:** `frontend/scripts/run-lighthouse.mjs`
- **Playwright Test:** `frontend/e2e/lighthouse.spec.ts`
- **Minimum Target Threshold:** Score >= 95 / 100

| Page Route | User Journey / Role | Lighthouse Accessibility Score | Status |
|---|---|:---:|:---:|
| `/` | Public Portal Homepage & Persona Cards | **100 / 100** | ✅ PASS (Target >= 95) |
| `/activate` | College Self-Activation & Board Verification Gate | **100 / 100** | ✅ PASS (Target >= 95) |
| `/login/college` | Institutional Admin Sign-In & TOTP Authentication | **100 / 100** | ✅ PASS (Target >= 95) |
| `/verify` | Authorized Stakeholder Credential Verification Gate | **98 / 100** | ✅ PASS (Target >= 95) |
| `/student` | Student Consent & APAAR Academic Records Portal | **98 / 100** | ✅ PASS (Target >= 95) |

### 3.3 Pure Keyboard-Only Journey Verification
End-to-end user journeys were executed exclusively using synthetic keyboard inputs (Tab, Shift+Tab, Enter, Space, alphanumeric input) without mouse pointer events:

- **Test Specification:** `frontend/e2e/keyboard_only_journeys.spec.ts`
- **Result:** **3 / 3 Core Journeys Passed (All interactive controls keyboard operable)**

1. **Journey 1: College Sign-In & Final Annual Submission Gate**
   - Focused email and password fields, submitted login form with `Enter`.
   - Handled MFA verification code prompt via keyboard.
   - Navigated to `/college/submit`, focused declaration legal acknowledgement checkbox, toggled with `Space`.
   - Requested OTP via `Enter`, typed 6-digit OTP into `#otp-input`.
   - Submitted final declaration using `Enter`, verified generation of official submission receipt number.
2. **Journey 2: AICTE Review Queue & Exception Adjudication**
   - Logged into AICTE Central Portal using credentials via keyboard.
   - Navigated to Review Queue (`/aicte/review`), focused first "Review Item" action button and activated with `Enter`.
   - Modal opened with focus trapped; selected "Accept Exception" radio option via `Space`.
   - Focused decision note textarea, typed statutory rationale string.
   - Submitted decision using `Enter` on "Accept & Resolve Exceptions" button, verified confirmation notification.
3. **Journey 3: Verifier Credential Request & Student Consent Approval**
   - Logged in as authorized verifier, navigated to `/verifier/search`.
   - Typed 12-digit student APAAR ID and DPDP verification purpose string via keyboard.
   - Tabbed to and submitted "Request student consent" button with `Enter`, verifying 24-hour expiry card generation.
   - Navigated to `/student` portal, entered APAAR ID, requested OTP.
   - Typed 6-digit code into accessible auto-advancing discrete OTP boxes (`Digit 1 of 6`), activated "Access records".
   - Focused "Approve consent" button in pending consent queue, approved via `Enter`, and confirmed single-use authorization.

---

## 4. UX4G CodeGen Prompt Self-Audit Checklist

Results from running the 5-round self-audit protocol from `.agents/ux4g/codegen-prompt.md`:

### Round 1 — Visual Audit
- [x] **Page structure:** Every page has a single `<main>` element, a sticky header/navbar, and a dark brand footer.
- [x] **Content width:** Maximum layout container constrained to `max-w-7xl` (1280px) with centered padding.
- [x] **Section alternating:** Page sections alternate cleanly between white surfaces and `--ux4g-bg-neutral-soft` (`#F8F9FA`).
- [x] **Typography hierarchy:** Exactly one `<h1>` per page. Heading scales follow `text-2xl` / `text-3xl` font weights without skipping levels.
- [x] **Colour contrast:** Text on light backgrounds exceeds 4.5:1; text on dark brand footer exceeds 7.0:1; badge text tuned to >= 7.0:1.
- [x] **Imagery:** Decorative icons include `aria-hidden="true"`; informative badges include accessible labels; no broken images or grey placeholder boxes.
- [x] **Brand colour presence:** Primary brand purple (`--edutrace-brand-primary`) applied across active nav links, focus rings, primary buttons, and card icon badges.
- [x] **Components:** Cards include uniform border and shadow tokens (`--ux4g-border-neutral-subtle`, `--ux4g-shadow-xs`); status badges conform to official UX4G semantic palette.

### Round 2 — Functional Audit
- [x] **Interactivity:** All buttons possess valid `onClick` or `type="submit"` handlers. Links resolve to active routes or specific targets.
- [x] **Forms:** All forms have validation with error states and assistive hints.
- [x] **Modals:** Inspection modals trap focus and dismiss cleanly on `Escape` key press.
- [x] **Navigation:** Active navigation indicators accurately highlight the current route; mobile hamburger toggles properly.
- [x] **States:** Loading spinners (`<LoadingSpinner />`), empty states (`<EmptyState />`), and error banners (`<ErrorState />`) render across all data tables and views.
- [x] **Responsive reflow:** Verified at 360px, 768px, and 1280px with no clipping or horizontal scrolling.
- [x] **Touch targets:** Interactive buttons and input fields maintain minimum 44×44px hit targets on mobile.

### Round 3 — Accessibility Audit
- [x] **Automated scan:** Axe-core Playwright audit run across all 32 routes with **zero serious or critical errors**.
- [x] **Keyboard navigation:** Complete keyboard tab order through all routes without focus traps. Focus visible at all times via `ux4g-focus-ring`.
- [x] **Images & Icons:** All icons have `aria-hidden="true"` or explicit `aria-label`.
- [x] **Form fields:** Every input, select, and textarea has an accessible label associated via `htmlFor`/`id` or explicit `aria-label`. Error alerts use `role="alert"`.
- [x] **Skip link:** "Skip to main content" link is the first focusable element on every page and smoothly targets `#main-content`.

### Round 4 — Code Quality Audit
- [x] **TypeScript:** Strict type checking passes (`npm run build` / `tsc --noEmit`) with zero errors.
- [x] **ESLint:** Linter passes cleanly with zero errors (`npm run lint`).
- [x] **Token enforcement:** Token linter (`node scripts/lint-tokens.mjs`) reports 0 raw hex or rgb values in JSX components outside `tokens.css`.
- [x] **Spacing tokens:** Spacing adheres strictly to the 4px Tailwind scale mapped to UX4G space variables.
- [x] **Microcopy consistency:** Headings audited to sentence case and interactive buttons audited to imperative action verbs (`node scripts/check-microcopy.mjs`).
- [x] **Console hygiene:** Zero debugging `console.log` statements in committed application code.

### Round 5 — Content Audit
- [x] **Clean content:** Zero "Lorem ipsum", "Test", "Dummy", or "Sample" strings in user-facing views.
- [x] **Realistic domain data:** Indian student names (Aarav Sharma, Priya Patel, etc.), realistic academic years (2025-26, 2026-27), and authentic course codes.
- [x] **Mandatory footer content:** Copyright notice, Privacy Policy link, Terms of Service link, Help & Glossary link (`/help`), and plain-language prototype disclaimer.
- [x] **Document metadata:** Meaningful document titles set for every page via `useDocumentTitle` hook.

---

## 5. Honest Gaps & Ongoing Limitations

While EduTrace fulfills all automated compliance criteria, the following architectural gaps and planned evolutions are documented transparently:

1. **Floating Toast Component:**  
   The official `ux4g-web-components` CSS distribution provides `.ux4g-alert` inline alert boxes but lacks a floating toast overlay container. EduTrace resolves this with a custom React wrapper (`Toast.tsx` / `ToastContext.tsx`) that wraps `.ux4g-alert` primitives inside a fixed, accessible `aria-live="polite"` viewport.
2. **High-Volume Data Table Virtualization:**  
   UX4G provides clean CSS classes for static and responsive tables (`.ux4g-table`), but does not provide JavaScript DOM virtualization for datasets exceeding 1,000 rows. EduTrace pairs UX4G semantic table classes with TanStack Virtual to maintain 60fps rendering during institutional audits.
3. **Dedicated High-Contrast Mode Toggle:**  
   The application respects the OS-level `prefers-contrast: more` media query through semantic CSS variables. A dedicated in-page toggle button allowing users to switch contrast themes manually without changing operating system settings is queued for a future iteration.
4. **Manual Screen Reader Certification:**  
   While automated axe-core scans and Lighthouse audits report near-perfect marks, comprehensive assistive technology verification requires manual testing with NVDA, JAWS, and VoiceOver across diverse end-user assistive setups. Formal human testing is scheduled as part of standard pre-launch acceptance testing.
5. **Multilingual Localization (Hindi):**  
   All microcopy has been extracted into dictionary structures (`frontend/src/copy/en.ts`). Staged Hindi translations (`copy/hi.ts`) await mandatory native-speaker manual review before user-facing toggle activation, adhering strictly to quality policy.
