# API Studio AI — UX Specification

## Product direction

API Studio AI is a focused workspace for building, understanding, and running API requests. It should have its own visual identity and feel professionally designed rather than familiar.

Do not imitate any existing product. Interaction patterns may follow industry standards when they improve usability, but visual design, spacing, layout, navigation, typography, and branding must remain original.

Avoid dashboard patterns that turn every feature into a CRUD card. Prefer a clear hierarchy, dense but breathable layouts, keyboard-friendly actions, subtle borders, and purposeful motion.

## Design system

This specification is governed by the accompanying design direction. API Studio AI must feel like a mature professional developer tool, not an AI-startup landing page or a generic SaaS dashboard.

### Product personality

The interface should communicate confidence, speed, precision, clarity, and engineering quality. It should feel calm and technical enough for experienced engineers to use every day. The interface should disappear behind the work.

### Product principle

The request builder is the heart of the application. Every other feature exists to improve the request-building and request-understanding workflow. Whenever there is a conflict between adding features and improving the request workflow, the request workflow always wins.

### First-principles rules

- Create an original identity. Borrow interaction patterns only when they improve usability; do not imitate another product.
- Remove decoration before removing functionality.
- Every visual decision must improve comprehension, navigation, or interaction.
- Prefer split layouts, resizable panels, collapsible navigation, persistent workspaces, and keyboard-first workflows.
- Optimize for developer information density, not screenshots.
- Empty states teach the feature and provide the next action; they do not use illustrations.
- Errors explain what happened, why it happened, and how to recover.

### No AI slop

Every screen must be intentionally designed. Never generate layouts that resemble generic AI-generated SaaS templates.

Avoid centered hero plus three cards, glowing gradients, floating glass panels, neon borders, oversized feature cards, meaningless statistics, fake charts, decorative illustrations, empty whitespace for aesthetics, repeated card grids, excessive rounded corners, dashboard-first layouts, placeholder avatars, and lorem ipsum testimonials.

Every section must solve a real user problem. Every component must have a functional purpose. Delete visual elements before adding new ones.

### Visual language

- The interface may support multiple themes. The default theme should prioritize readability during long engineering sessions. Color palettes should emerge from the design system rather than being fixed in this document.
- Inter or Geist for UI text; JetBrains Mono for URLs, code, JSON, and metadata.
- 4px spacing base; generous page gutters; 6–10px radii; 1px low-contrast borders.
- Color communicates state: green success, amber warning, red failure, blue information, violet AI.
- No decorative gradients, glowing cards, or oversized illustrations in the application shell.
- Every primary action has a keyboard shortcut and visible hover/focus state.
- Neutral interface surfaces should remain clear even if all accent colors are removed.
- Do not use purple gradients, glowing cards, glassmorphism, neon borders, floating blobs, oversized illustrations, generic SaaS cards, meaningless charts, decorative shadows, or excessive rounded corners.
- Buttons are understated, tables are information-dense, forms are simple, dialogs are lightweight, and menus open instantly.
- Typography, spacing, alignment, and contrast create hierarchy before color, scale, or effects.

### Motion and performance

Motion explains state changes and never exists for decoration. Transitions should be fast, subtle, and predictable. Respect reduced-motion preferences, avoid layout shifts, preserve context during loading, and avoid unnecessary loading animations.

### Accessibility and responsive behavior

Target WCAG 2.2 AA with keyboard navigation, visible focus, semantic HTML, screen-reader support, high contrast, and reduced motion. Desktop is the primary platform, tablet is supported, and mobile focuses on viewing and lightweight editing without compromising desktop workflows.

### Component philosophy

Every component should solve exactly one problem. Components should not exist because other products have them. Buttons trigger actions. Panels contain related information. Cards group content only when hierarchy requires it. Avoid decorative containers and nested cards; prefer layout over decoration.

### Design tokens

Use these tokens as the default vocabulary. A screen may introduce a token only when a documented product need requires it.

| Token | Values |
| --- | --- |
| Spacing | 4, 8, 12, 16, 20, 24, 32, 40, 48px |
| Radius | 6, 8, 10px |
| Border | 1px |
| Elevation | 0, 1, 2 |
| Animation | 120, 180, 250ms |

Use neutral surfaces by default. Accent and status colors are semantic only: interaction, success, warning, error, information, and active selection. Themes must preserve hierarchy and readability without relying on a particular palette.

### Screen design process

Before designing any screen:

1. Identify the primary user goal.
2. Identify the most frequent workflow.
3. Sketch the information hierarchy.
4. Decide what is always visible.
5. Decide what is contextual.
6. Build the layout.
7. Add interactions.
8. Add visual styling last.

Never start from colors or components. Always start from the user workflow.

### UX rules

- Never hide primary actions.
- Every page has one obvious primary action.
- Never place destructive actions next to primary actions.
- Secondary actions must not compete visually.
- Users should understand the page within five seconds.
- Important information must not be hidden inside accordions.
- Confirmation dialogs are reserved for destructive actions.
- Prefer inline editing when it provides a better workflow than a modal.

### Visual balance

Do not force perfect symmetry. Allow layouts to breathe. Large working areas should dominate the interface, while secondary navigation should visually recede.

The eye should naturally move from navigation, to the current task, to supporting tools, and finally to secondary information. Do not make every panel visually equal. Hierarchy is more important than symmetry.

### Screen evolution

Never redesign existing screens without a strong product reason. Every new feature must extend the current interface and preserve user muscle memory. Avoid moving primary actions or changing navigation casually. Prefer evolution over redesign so the product grows naturally over time.

### Mandatory design iteration

Every screen must go through at least three internal iterations before being considered complete.

1. Iteration 1: focus only on the workflow.
2. Iteration 2: improve hierarchy, spacing, and interaction.
3. Iteration 3: remove unnecessary UI elements and simplify.

Do not present the first design immediately. Critique it first: identify what works, what feels generic, what should be removed, and what can be simplified. Only present the final refined version.

## Information architecture

Top navigation: workspace switcher, global search/command menu, documentation link, notifications, user menu.

Workspace rail: Collections, Environments, History, AI, and Settings. The rail is compact and collapsible, not a large permanent sidebar.

Main workspace: tabbed requests above the request builder; response viewer below or beside it depending on viewport.

AI panel: persistent right-side panel that can be resized or hidden. It is a workspace tool, not a floating chat bubble.

## Screens

### Landing page

Purpose: explain the product and move developers to “Start building”.

Sections: top navigation; hero with concise value proposition and animated API request demo; trusted-by strip; AI capabilities; import from existing API clients, OpenAPI, or cURL; feature grid; product screenshots; pricing; testimonials; final CTA; footer.

The hero demo should show a realistic request moving from draft to response, with restrained syntax highlighting and a visible AI suggestion. Motion should clarify the workflow and respect reduced-motion preferences.

### Authentication

Provide sign in, create account, and reset password states in one calm centered layout. Support email/password initially, with space for OAuth later. Explain data privacy briefly. Show validation inline and preserve entered values after recoverable errors.

### Dashboard / workspace home

After sign-in, land in the workspace rather than a metrics dashboard. Show recent requests, collections, environments, and a prominent “New request” action. Include import shortcuts and a compact activity feed. Empty states should teach the first workflow: create, import, or open a recent request.

### Collections

Use a tree/list view with collections, folders, and requests. Support create, rename, duplicate, move, delete, import, and export. Selecting a request opens it as a tab in the main workspace. Use contextual menus and drag-and-drop only as enhancements; all actions must remain keyboard accessible.

### Request builder

Primary row: method selector, URL field, Send, Save, AI Generate, and Import cURL.

Request tabs: Params, Authorization, Headers, Body, Scripts, Settings. Use editable key/value rows with clear enable toggles, secret masking, environment-variable autocomplete, and unsaved-change indicators.

The request builder is the primary differentiator and must feel like a persistent workbench.

Support pinned request tabs, unsaved-change indicators, duplicate-tab, split-view, command-palette access, quick headers, environment-variable autocomplete, recent URLs, request templates, execution status, and live validation. Tabs preserve drafts independently. Split view must make request/response comparison easier without forcing navigation. The URL field should recognize pasted URLs and suggest recent values. Request templates should be discoverable without interrupting the current draft.

The builder must support URL paste, method-aware defaults, request cancellation, loading states, and a readable error state. Save should make the collection destination explicit when needed.

### Response viewer

Show status, duration, size, and response actions at the top. Tabs: Pretty, Raw, Headers, Cookies, Timeline, Console. Pretty JSON/XML should have syntax highlighting, folding, copy, search, and line numbers where useful. Long responses need virtualization or a clear truncation affordance.

### Environment manager

List environments with active-state control. Provide variable name, value, secret flag, and enabled state. Distinguish current, local, and shared values. Mask secrets by default and require an explicit reveal action. Show which variables are used by the current request.

### History

Present a searchable chronological list grouped by day, with method, URL, status, duration, and environment. Opening an item restores it as a new request tab. Allow replay and save-to-collection. Make clear that history can contain sensitive request data and provide retention/clear controls.

### AI assistant

Persistent right-side panel with conversation context tied to the current request and response. Primary actions: Explain, Generate, Modify, Execute. Suggested prompts should be contextual, such as “Explain this 401” or “Create tests for this response”.

AI-generated changes must appear as a diff or preview before applying. Execute always requires a visible confirmation when it changes data or uses a non-local environment. Show model activity, tool steps, errors, and an undo path without overwhelming the request workspace.

AI should observe the workspace, never interrupt the user, explain before changing, and preview every modification. It must never perform destructive actions without confirmation. It remembers only the current workspace context, disappears when not needed, and never becomes the visual center of the application. The request builder remains primary.

### UI state rules

Every page and major component must define loading, empty, success, error, offline, permission denied, expired session, long-running operation, and partial-failure states. No screen is complete until all applicable states are designed. State transitions must preserve user context and draft data wherever possible.

### Settings

Organize into Profile, Workspace, Appearance, Shortcuts, Integrations, AI Providers, Data & Privacy, and Danger Zone. Keep destructive actions isolated and explicit. Workspace settings should distinguish personal preferences from shared configuration.

## Core interaction rules

- Command menu: `⌘/Ctrl + K` for navigation, actions, and request search.
- New request: `⌘/Ctrl + N`; send request: `⌘/Ctrl + Enter`; save: `⌘/Ctrl + S`.
- Tabs preserve draft state and warn before closing unsaved changes.
- Toasts confirm completed actions; inline errors explain how to recover.
- Loading states use skeletons or progress indicators that preserve layout.
- Responsive behavior collapses the workspace rail and AI panel before reducing request-builder usability.
- Accessibility target: WCAG 2.2 AA, visible focus rings, full keyboard navigation, semantic labels, and reduced-motion support.

## Implementation order

1. Establish design tokens and application shell.
2. Build authentication and workspace home.
3. Build request tabs, request builder, and response viewer.
4. Add collections, environments, and history using the existing backend modules.
5. Add the contextual AI panel and guarded actions.
6. Build the marketing landing page and pricing/testimonial content.
7. Add polish: shortcuts, motion, responsive states, accessibility, and visual QA.

## Design review gate

Before accepting any screen, verify that it improves the workflow, reuses this design system, supports keyboard and accessible interaction, and remains balanced without decorative effects. An experienced developer should be able to use it for hours without feeling distracted by the interface.

Ask:

- What is the user trying to accomplish?
- Can one component be removed?
- Can one interaction be simplified?
- Is any information duplicated?
- Is there unnecessary decoration?
- Would this still look good in grayscale?
- Can it be used entirely with the keyboard?
- Would an experienced developer enjoy using it for eight hours?
- Does it remain original after removing the colors?
