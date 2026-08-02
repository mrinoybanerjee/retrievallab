type IconName = "spark" | "chart" | "book" | "code" | "github" | "sliders" | "chevron" | "play" | "close" | "arrow" | "check" | "search";

export function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, React.ReactNode> = {
    spark: <><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><path d="m6.4 6.4 2.1 2.1M15.5 15.5l2.1 2.1M17.6 6.4l-2.1 2.1M8.5 15.5l-2.1 2.1"/><circle cx="12" cy="12" r="3.5"/></>,
    chart: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5z"/></>,
    code: <><path d="m8 9-3 3 3 3M16 9l3 3-3 3M14 5l-4 14"/></>,
    github: <path d="M15 22v-4.1c.04-1-.35-1.75-1-2.2 3.28-.37 6.72-1.61 6.72-7.28A5.7 5.7 0 0 0 19.2 4.5 5.3 5.3 0 0 0 19.05.6S17.85.2 15 2.1a13.4 13.4 0 0 0-7 0C5.15.2 3.95.6 3.95.6A5.3 5.3 0 0 0 3.8 4.5a5.7 5.7 0 0 0-1.52 3.92c0 5.65 3.43 6.9 6.7 7.28-.42.37-.8 1.02-.93 1.98-.84.38-2.97 1.03-4.28-1.22 0 0-.78-1.42-2.26-1.52 0 0-1.44-.02-.1.9 0 0 .97.45 1.64 2.14 0 0 .87 2.87 4.95 1.9V22"/>,
    sliders: <><path d="M4 7h8M16 7h4M4 17h4M12 17h8"/><circle cx="14" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    play: <path d="m8 5 11 7-11 7z"/>,
    close: <><path d="m6 6 12 12M18 6 6 18"/></>,
    arrow: <><path d="M5 12h14M14 7l5 5-5 5"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  };
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
