"""Standing rules consulted before any code is written.

His instruction (WhatsApp voice note, 2026-11-13): the ponytail and no-ai-slop repos are always
consulted before writing code. Both MIT (commercial-safe); pins in docs/REUSE.md. These are
faithful distillations, not verbatim copies:
- DietrichGebert/ponytail AGENTS.md: lazy senior dev, the smallest complete change.
- petergyang/no-ai-slop SKILL.md: AI-slop patterns banned from emitted prose.
"""

PONYTAIL = (
    "Smallest complete change, in order: [1] Does it need to exist? Skip features nobody asked for. "
    "[2] Already in this codebase? Use it the way surrounding code does. [3] Standard library or a "
    "platform feature? Use it. [4] An installed dependency? Use it; never add one for a few lines. "
    "[5] One clear line. [6] Otherwise the minimum code that works. No abstraction, wrapper, option "
    "or 'for later' code nobody asked for; deletion beats addition; keep the codebase's structure. "
    "Be lazy about the solution, never about the change: finish callers, tests and fixtures your "
    "change breaks. Bug fix: grep every caller, fix the root cause once in shared code. New "
    "non-trivial logic leaves one small test. A shortcut with a known limit gets a comment "
    "`shortcut: <limit>, <when to upgrade>`. Never cut: validation at trust boundaries, error "
    "handling that prevents data loss, security, accessibility, anything the user asked for."
)

NO_AI_SLOP = (
    "No AI slop in emitted prose (docs, comments, reports). Banned words: delve, foster, leverage, "
    "utilize, facilitate, empower, streamline, robust, cutting-edge, paradigm shift, game changer, "
    "tapestry, realm, beacon, multifaceted, meticulous, intricate, paramount, transformative, "
    "elevate, embark, supercharge, harness, ever-evolving. Banned patterns: throat-clearing openers; "
    "'not X but Y' contrasts; colon reveals; trailing -ing analysis clauses (highlighting, "
    "underscoring); importance puffery (pivotal, vital role); weasel attribution (experts agree, "
    "studies show) - name the source or cut; fake-strong verbs (serves as); synonym cycling; "
    "negative listing; dramatic fragmentation; rhetorical setups; fake-profound kickers; "
    "summary-recap endings; decorative bold/emoji formatting."
)

NEVER_LIE = (
    "Never claim done, complete, fixed or finished unless the checks for it exited 0. "
    "Partially built is reported as 'partially built', naming exactly what is missing and what "
    "was verified. When unsure, say what was checked and what was not. His 2026-11-13 voice "
    "note: fake 'done' promises are what users hate in current IDEs; this harness never makes "
    "one."
)
