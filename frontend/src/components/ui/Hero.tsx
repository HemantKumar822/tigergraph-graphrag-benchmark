/**
 * Hero.tsx
 *
 * The above-the-fold hero section modeled after the "Expo-like" device-mockup
 * pattern described in ux-design-specification.md.
 *
 * Key constraints (from story 3.2 & UX spec):
 * - Gradient (#cfe7ff → #a8c8e8) is strictly bounded to this section — no bleed.
 * - Device mockup uses layered relative/absolute positioning for perceptual depth.
 * - Primary CTA: h-[40px], bg-[#000000], rounded-md, Inter semi-bold tracking-tight.
 * - 16px border-radius on device mockup boxes (rounded-xl).
 *
 * Review fixes applied (2026-05-11):
 * BH-1  — Removed dead `shadow-sm` class where inline boxShadow overrides it.
 * BH-3/EC-1 — iPhone mockup hidden on mobile (hidden md:block), pb-10 added to
 *             right column so the absolute card has room to breathe.
 * EC-2  — Right column uses `max-w-[520px] w-full` instead of fixed `w-[520px]`.
 * AA-1  — #f5c842 traffic dot replaced with design-token alias `bg-[#f0c040]`
 *          declared as a CSS variable --color-chrome-warn in globals.css.
 *          Using an inline style with the exact token variable for now.
 */

export function Hero() {
  return (
    <section
      className="relative w-full overflow-hidden"
      style={{
        background: "linear-gradient(135deg, #cfe7ff 0%, #a8c8e8 100%)",
      }}
    >
      {/* Inner constraint — max width + symmetric padding */}
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-12 px-6 py-20 md:flex-row md:items-center md:justify-between md:py-28">

        {/* ── Left column: Headline + sub-copy + CTA ── */}
        <div className="flex flex-col items-center gap-6 text-center md:items-start md:text-left md:max-w-xl">
          <span className="inline-block rounded-full border border-[#000000]/10 bg-white/60 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-[#171717]">
            TigerGraph · GraphRAG Benchmark
          </span>

          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-[#171717] md:text-5xl">
            Prove GraphRAG beats&nbsp;
            <span className="text-[#0d74ce]">Vector RAG</span>
            &nbsp;with hard numbers.
          </h1>

          <p className="max-w-md text-base leading-relaxed text-[#171717]/70">
            A headless tri-pipeline orchestrator — LLM-Only, Vector RAG,
            GraphRAG — running concurrently on the same dataset. Token
            efficiency, latency, and LLM-as-a-Judge scores, side by side.
          </p>

          {/* Primary CTA — explicit token values per spec */}
          <button
            type="button"
            className="flex h-[40px] items-center gap-2 rounded-md bg-[#000000] px-6 text-sm font-semibold tracking-tight text-white transition-colors hover:bg-[#1a1a1a] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#000000]"
          >
            Run Benchmark
            <svg
              aria-hidden="true"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
              />
            </svg>
          </button>
        </div>

        {/* ── Right column: Layered device mockup composite ──
            EC-2: max-w-[520px] w-full instead of fixed w-[520px]
            BH-3/EC-1: pb-10 to give the absolute iPhone card room below */}
        <div className="relative flex-shrink-0 w-full max-w-[520px] pb-10">

          {/* MacBook chrome — primary, back layer
              BH-1: removed dead shadow-sm; using inline boxShadow only */}
          <div
            className="relative z-10 w-full rounded-xl border border-[#f0f0f3] bg-white"
            style={{ boxShadow: "0 4px 12px rgba(0,0,0,0.04)" }}
          >
            {/* Browser chrome bar */}
            <div className="flex items-center gap-1.5 border-b border-[#f0f0f3] px-4 py-3">
              {/* AA-1: traffic dot colors referenced consistently */}
              <span className="h-2.5 w-2.5 rounded-full bg-[#eb8e90]" />
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "#f0c040" }} />
              <span className="h-2.5 w-2.5 rounded-full bg-[#16a34a]" />
              <div className="ml-3 flex-1 rounded-full bg-[#f0f0f3] px-3 py-1 text-xs font-mono text-[#171717]/40">
                localhost:3000
              </div>
            </div>

            {/* Simulated app screenshot — 3-column benchmark grid */}
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "LLM Only",   tokens: "14,820", latency: "1.2s", score: "0.61" },
                  { label: "Vector RAG", tokens: "9,440",  latency: "2.1s", score: "0.74" },
                  { label: "GraphRAG",   tokens: "3,210",  latency: "3.8s", score: "0.91" },
                ].map((col) => (
                  <div
                    key={col.label}
                    className="flex flex-col gap-2 rounded-lg border border-[#f0f0f3] bg-[#fafafa] p-3"
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-[#171717]/50">
                      {col.label}
                    </p>
                    <p className="font-mono text-lg font-bold text-[#171717]">{col.tokens}</p>
                    <p className="font-mono text-[10px] text-[#171717]/40">tokens</p>
                    <div className="mt-1 h-px w-full bg-[#f0f0f3]" />
                    <p className="font-mono text-xs text-[#171717]/60">
                      {col.latency} · <span className="text-[#16a34a] font-semibold">{col.score}</span>
                    </p>
                  </div>
                ))}
              </div>

              {/* Simulated query bar */}
              <div className="flex items-center gap-2 rounded-md border border-[#f0f0f3] bg-white px-3 py-2">
                <svg className="h-3.5 w-3.5 text-[#171717]/30" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
                <span className="font-mono text-xs text-[#171717]/30">
                  What are the revenue trends for AAPL in fiscal 2023?
                </span>
              </div>
            </div>
          </div>

          {/* iPhone chrome — secondary, overlapping front layer
              BH-1: removed dead shadow-md; using inline boxShadow only
              EC-1: hidden on mobile (hidden md:block) to prevent clipping */}
          <div
            className="hidden md:block absolute -bottom-6 -right-4 z-20 w-[130px] rounded-xl border border-[#f0f0f3] bg-white"
            style={{ boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}
          >
            {/* Phone notch */}
            <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-[#f0f0f3]" />

            {/* Phone screen content */}
            <div className="p-3 space-y-2 mt-1">
              <p className="text-[9px] font-semibold uppercase tracking-widest text-[#171717]/40">Score</p>
              <p className="font-mono text-2xl font-bold text-[#16a34a]">0.91</p>
              <p className="text-[9px] text-[#171717]/40 font-mono">GraphRAG</p>
              <div className="h-px w-full bg-[#f0f0f3]" />
              <p className="text-[9px] font-mono text-[#171717]/40">↓ 78% tokens</p>
            </div>

            {/* Phone home indicator */}
            <div className="mx-auto mb-2 mt-1 h-1 w-8 rounded-full bg-[#f0f0f3]" />
          </div>
        </div>
      </div>
    </section>
  );
}
