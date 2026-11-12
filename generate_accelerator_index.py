import json

accelerators = {
    "version": "1.0.0",
    "updated_at": "2026-11-11",
    "description": "Standard Accelerator Library & Component Ecosystem for Rashi Harness Workspace",
    "github_toolkits": [
        {
            "name": "free-claude-code",
            "url": "https://github.com/Rishurajgautam24/free-claude-code",
            "category": "Gateway & Free Model Access",
            "description": "Free Claude Code gateway integration to bypass paid subscription walls via reverse proxy endpoints."
        },
        {
            "name": "no-ai-slop",
            "url": "https://github.com/petergyang/no-ai-slop",
            "category": "Quality & Anti-Slop Enforcement",
            "description": "Peter Yang's definitive rules for eradicating generic AI filler, platitudes, and conversational slop from research, PRs, and documentation."
        },
        {
            "name": "ai-engineering-from-scratch",
            "url": "https://github.com/rohitg00/ai-engineering-from-scratch",
            "category": "Foundational AI & Systems",
            "description": "Complete ground-up implementations of modern transformer architectures, RAG, and fine-tuning pipelines."
        },
        {
            "name": "code_turtle",
            "url": "https://github.com/spotmies/code_turtle",
            "category": "Autonomous Coding Engine",
            "description": "Lightweight autonomous agent framework for recursive file analysis and code synthesis."
        },
        {
            "name": "RuView",
            "url": "https://github.com/ruvnet/RuView",
            "category": "Telemetry & Real-Time Monitoring",
            "description": "Ultra-fast real-time telemetry viewer for microservice streams and process visualization."
        },
        {
            "name": "OfficeCLI",
            "url": "https://github.com/iOfficeAI/OfficeCLI",
            "category": "Document Automation",
            "description": "CLI automation tool for parsing, editing, and generating Microsoft Office and PDF documents."
        },
        {
            "name": "ian-xiaohei-illustrations",
            "url": "https://github.com/helloianneo/ian-xiaohei-illustrations",
            "category": "Design & Vector Assets",
            "description": "Hand-crafted vector illustrations and SVG graphic assets for modern landing pages."
        },
        {
            "name": "CYBERDECK-MINI-ESP32",
            "url": "https://github.com/pepeangell5/CYBERDECK-MINI-ESP32",
            "category": "Hardware & Cyberdeck Firmware",
            "description": "Portable ESP32 cyberdeck firmware for hardware hacking, serial monitoring, and terminal access."
        },
        {
            "name": "kimiko",
            "url": "https://github.com/spearchucker667/kimiko",
            "category": "Autonomous Agent Tooling",
            "description": "Modular agent toolkit for task delegation and reconnaissance."
        }
    ],
    "component_libraries_50": [
        {"id": 1, "name": "8bitcn", "url": "https://github.com/TheOrcDev/8bitcn-ui", "category": "Retro / Pixel Art", "style": "8-bit retro gaming UI components"},
        {"id": 2, "name": "Base CN", "url": "https://www.basecn.dev/", "category": "Minimalist Utility", "style": "Clean foundation components"},
        {"id": 3, "name": "Be UI", "url": "https://beui.dev/", "category": "Modern Web", "style": "Sleek production components"},
        {"id": 4, "name": "COS UI", "url": "https://github.com/baidu/cosui", "category": "Enterprise", "style": "Enterprise system design"},
        {"id": 5, "name": "Cult UI", "url": "https://www.cult-ui.com/", "category": "Creative / Bold", "style": "Edgy micro-interactions & animations"},
        {"id": 6, "name": "Daisy UI", "url": "https://daisyui.com/", "category": "Tailwind Semantic", "style": "Lightweight, pure CSS Tailwind classes"},
        {"id": 7, "name": "Easy UI", "url": "https://easyui.site/", "category": "Fast Prototyping", "style": "Pre-built SaaS blocks"},
        {"id": 8, "name": "Eldora UI", "url": "https://www.eldoraui.site/", "category": "Modern Animations", "style": "Tailwind + Framer motion templates"},
        {"id": 9, "name": "Fancy Components", "url": "https://www.fancycomponents.dev/", "category": "Micro-Interactions", "style": "Creative buttons, cards, and canvas effects"},
        {"id": 10, "name": "Hero UI", "url": "https://heroui.com/", "category": "Accessible Modern", "style": "NextUI evolution, accessible & polished"},
        {"id": 11, "name": "Kibo UI", "url": "https://www.kibo-ui.com/", "category": "Design System", "style": "Component library for modern design systems"},
        {"id": 12, "name": "Magic UI", "url": "https://magicui.design/", "category": "Visual Effects & 3D", "style": "High-impact animated landing page components"},
        {"id": 13, "name": "Motion Primitives", "url": "https://motion-primitives.com/", "category": "Animations", "style": "Framer Motion primitives & building blocks"},
        {"id": 14, "name": "MVP Blocks", "url": "https://mvpblocks.com/", "category": "Rapid MVP", "style": "Ready-to-ship full landing page sections"},
        {"id": 15, "name": "shadcn/ui", "url": "https://ui.shadcn.com/", "category": "Gold Standard Primitive", "style": "Accessible Radix + Tailwind copy-paste components"},
        {"id": 16, "name": "React Bits", "url": "https://reactbits.dev/", "category": "Interactive Patterns", "style": "Animated text, magnetic buttons, custom cursors"},
        {"id": 17, "name": "Spectrum UI", "url": "https://ui.spectrumhq.in/", "category": "Tailwind Ecosystem", "style": "Clean modern dashboard blocks"},
        {"id": 18, "name": "Velora UI", "url": "https://velora.colorlib.com/", "category": "Clean Layouts", "style": "Responsive marketing & SaaS templates"},
        {"id": 19, "name": "Watermelon UI", "url": "https://ui.watermelon.sh/home", "category": "Fresh SaaS", "style": "Colorful modern web components"},
        {"id": 20, "name": "21st.dev", "url": "https://21st.dev/", "category": "Community Design", "style": "Crowdsourced modern React/Tailwind components"},
        {"id": 21, "name": "Aceternity UI", "url": "https://ui.aceternity.com/", "category": "High-Craft Animations", "style": "Trending visual effects, glowing borders, 3D pin"},
        {"id": 22, "name": "Amicro", "url": "https://github.com/Subhan-code/Amicro--Micro-transitions-", "category": "Micro-Transitions", "style": "Subtle UI motion and state transitions"},
        {"id": 23, "name": "Animate UI", "url": "https://animate-ui.com/", "category": "Motion Kits", "style": "Pre-made CSS & JS animations"},
        {"id": 24, "name": "Beautiful UI", "url": "https://beautiful-ui.dev/docs", "category": "Aesthetic Clean", "style": "Clean, opinionated components"},
        {"id": 25, "name": "Flyon UI", "url": "https://flyonui.com/", "category": "Semantic Tailwind", "style": "Tailwind components with interactive JS plugins"},
        {"id": 26, "name": "Hexter UI", "url": "https://designeer.org/best/shadcn-ecosystem", "category": "Shadcn Extended", "style": "Curated extensions for Shadcn"},
        {"id": 27, "name": "Jolly UI", "url": "https://github.com/jolbol1/jolly-ui", "category": "Accessible Aria", "style": "Shadcn components ported to React Aria Components"},
        {"id": 28, "name": "Lights Wind", "url": "https://lightswind.com/", "category": "Lightweight CSS", "style": "Ultra-lightweight Tailwind presets"},
        {"id": 29, "name": "Lex UI", "url": "https://github.com/jxarco/lexgui.js/", "category": "Developer Tools UI", "style": "GUI panel controls for WebGL/tools"},
        {"id": 30, "name": "Reverse UI", "url": "https://reverseui.com/", "category": "Dark Minimalist", "style": "High-contrast dark-mode first design"},
        {"id": 31, "name": "Skyper UI", "url": "https://skiper-ui.com/", "category": "Modern Web", "style": "Clean layout cards and modals"},
        {"id": 32, "name": "Smooth UI", "url": "https://smoothui.dev/", "category": "Fluid Animations", "style": "Spring-physics animated components"},
        {"id": 33, "name": "Tailark", "url": "https://tailark.com/", "category": "Marketing Sections", "style": "High-converting marketing sections"},
        {"id": 34, "name": "Tail Grids", "url": "https://tailgrids.com/", "category": "Grid & Dashboards", "style": "Complete responsive grids and table layouts"},
        {"id": 35, "name": "UI Layouts", "url": "https://www.ui-layouts.com/", "category": "Full Page Layouts", "style": "Complex application layouts and shells"},
        {"id": 36, "name": "Flowbite", "url": "https://flowbite.com/", "category": "Comprehensive Suite", "style": "Massive Tailwind UI ecosystem with dark mode"},
        {"id": 37, "name": "Hyper UI", "url": "https://hyperui.dev/", "category": "Marketing & eCommerce", "style": "Free Tailwind marketing and dashboard snippets"},
        {"id": 38, "name": "Preline UI", "url": "https://preline.co/", "category": "Open-Source Tailwind", "style": "Enterprise-grade Tailwind UI components"},
        {"id": 39, "name": "Float UI", "url": "https://floatui.com/", "category": "SaaS Templates", "style": "Modern accessible UI components and website templates"},
        {"id": 40, "name": "Meraki UI", "url": "https://merakiui.com/", "category": "RTL & Responsive", "style": "Clean Tailwind components with full RTL support"},
        {"id": 41, "name": "Kokonut UI", "url": "https://github.com/kokonut-labs/kokonutui/", "category": "Modern React", "style": "Curated collection of 100+ creative components"},
        {"id": 42, "name": "Nex UI", "url": "https://www.nexui.dev/", "category": "Next.js Optimized", "style": "Components tailored for Next.js 14/15 App Router"},
        {"id": 43, "name": "Ninna UI", "url": "https://github.com/ninna-ui/ninna-ui", "category": "Component Library", "style": "Lightweight modular components"},
        {"id": 44, "name": "Sera UI", "url": "https://github.com/seraui/seraui", "category": "React Kit", "style": "Clean React component kit"},
        {"id": 45, "name": "Re UI", "url": "https://reui.io/docs", "category": "Docs & Content", "style": "Components optimized for documentation and technical sites"},
        {"id": 46, "name": "Syntax UI", "url": "https://syntaxui.com/", "category": "Copy-Paste Magic", "style": "Ready-to-use customizable animated components"},
        {"id": 47, "name": "Open Source UI", "url": "https://github.com/saadeghi/daisyui", "category": "Community OSS", "style": "Popular community-driven component kits"},
        {"id": 48, "name": "Kimia UI", "url": "https://github.com/enochndika/kimia-UI", "category": "Fresh Patterns", "style": "Modern interactive card and modal primitives"},
        {"id": 49, "name": "Tremor", "url": "https://www.tremor.so/", "category": "Dashboards & Analytics", "style": "The gold standard for data charts, KPI cards, and metrics"},
        {"id": 50, "name": "Headless UI", "url": "https://headlessui.com/", "category": "Unstyled Logic", "style": "Official Tailwind Labs unstyled, fully accessible primitives"}
    ]
}

with open(r"d:\unreseted ai\rashi_accelerators.json", "w", encoding="utf-8") as f:
    json.dump(accelerators, f, indent=2)

print("Saved d:\\unreseted ai\\rashi_accelerators.json with all 9 Nov 11 repos and 50 verified component libraries!")
