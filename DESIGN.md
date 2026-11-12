# RakshEx Enterprise Design System Specification (DESIGN.md)
*Standardized for Autonomous Multi-Agent UI Generation & Human-in-the-Loop War Rooms*

---

## 1. Architectural Influences & Big Tech Open-Source Lineage

### A. Meta Platforms
- **Meta Astryx (`meta/astryx`)**: 
  - Standardized on React 19+ and **StyleX** token compilation.
  - Utilizes machine-readable component contracts designed specifically for AI coding agents to compose layouts without drifting from accessibility and token rules.
  - Decoupled behavior/accessibility from visual theme tokens via CSS custom properties.
- **Lexical (`facebook/lexical`)**: Extensible rich-text log engine for the terminal stream.

### B. Enterprise Giants
- **GitHub Primer (`primer/react`)**: High-density branch visualizers, diff viewers, and security vulnerability alert states.
- **IBM Carbon (`carbon-design-system`)**: Telemetry badges, hardware metrics, cluster status indicators, and operational monitors.
- **Vercel / Radix UI / shadcn/ui**: Headless keyboard-accessible primitives combined with Tailwind utility tokens.

### C. Curated High-Motion & Cyberpunk Frameworks
- **21st.dev & Magic UI (`@dillionverma`)**: Animated glowing tracing beams, border beams, and spring-physics bento grids.
- **Aceternity UI**: Spotlight cursor follow effects, background grid rays, 3D card perspective tilt.
- **Cult UI & Hover.dev**: Cyberpunk noise textures, brutalist status tags, and magnetic interaction states.
- **beui.dev & CrafterUI**: Zero-dependency animated micro-interactions for live terminal feeds.

---

## 2. Core Color Palette & Design Tokens

```css
:root {
  /* Surfaces */
  --surface-base: #030712;          /* True Void Black */
  --surface-card: rgba(17, 24, 39, 0.7); /* Translucent Midnight Gray */
  --surface-border: rgba(255, 255, 255, 0.08);
  --surface-border-active: rgba(56, 189, 248, 0.4);

  /* Functional Status Accents */
  --status-gate: #fbbf24;           /* Jev 1.13 Decision Gold */
  --status-builder: #818cf8;        /* Qwen / GLM Indigo */
  --status-adversary: #fb7185;      /* DeepSeek Rose */
  --status-verified: #34d399;       /* Verified Consensus Emerald */
  --status-telemetry: #38bdf8;      /* Data Stream Sky Blue */
  --status-memory: #c084fc;         /* Second Brain Purple */
}
```

---

## 3. Component Architecture Guidelines

### 1. Bento Grid Cards (`bento-card`)
- **Container**: `backdrop-blur-md`, subtle 1px border (`rgba(255, 255, 255, 0.08)`).
- **Hover Micro-interaction**: Dynamic spotlight gradient following mouse pointer via CSS variable `--mouse-x`, `--mouse-y`.
- **Corner Radius**: Standardized 8px (`rounded-lg`) for enterprise density.

### 2. Live Telemetry Particles (Canvas Flow)
- Dynamic Canvas 2D engine rendering real-time vector links between:
  - **APInex Web Discovery Node**
  - **Builder Specialist Nodes** (Qwen 3.8 / GLM 5.3)
  - **Adversarial Audit Nodes** (DeepSeek V4 Pro)
  - **Decision Gate** (Jev 1.13)
- Real-time packet collisions trigger instant terminal lines and state commit events in the Second Brain WAL.

### 3. Adversarial Debate Terminal
- High-density monospace font (`JetBrains Mono`, 11px).
- Color-coded log levels:
  - Cyan `[DISCOVERY]`: Open-source repository search.
  - Purple `[BUILDER_PROPOSAL]`: Structural patch submissions.
  - Rose `[ADVERSARIAL_CHALLENGE]`: Red-team exploit attempt.
  - Emerald `[EMPIRICAL_DEFENSE]`: Verifiable proof benchmark.
  - Gold `[JEV_VERDICT]`: Formal calibrated probability score.

---

## 4. Curated Reference Directory
- **Components & Sections**: `21st.dev` (Magic UI, Ruixen UI), `beui.dev`, `crafterui.com`
- **Layout & Mobile UX**: `mobbin.com`, `land-book.com`, `recent.design`
- **Micro-Interactions**: `microkit.co`, `motionin.design`, `60fps.design`
- **AI Design Rules**: `devault.design/design-md`, `open-design.ai`
