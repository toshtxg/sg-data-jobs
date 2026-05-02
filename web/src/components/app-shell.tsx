"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  BriefcaseBusiness,
  LayoutDashboard,
  Search,
} from "lucide-react";
import { useState, type MouseEvent, type ReactNode } from "react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Job Explorer", icon: Search },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [pendingHref, setPendingHref] = useState<string | null>(null);

  function isActiveHref(href: string) {
    return href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(`${href}/`);
  }

  function handleNavClick(event: MouseEvent<HTMLAnchorElement>, href: string) {
    if (
      event.defaultPrevented ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      event.button !== 0 ||
      isActiveHref(href)
    ) {
      return;
    }
    setPendingHref(href);
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed left-0 top-0 z-20 hidden h-screen w-64 border-r border-line bg-[#14161b] px-4 py-5 lg:block">
        <Link href="/" className="flex items-center gap-3 rounded-md px-2 py-2">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-accent text-[#07110f]">
            <BriefcaseBusiness size={20} />
          </span>
          <span>
            <span className="block text-sm font-semibold">SG Data & AI Job Pulse</span>
            <span className="block text-xs text-muted">MCF / FCF live scan</span>
          </span>
        </Link>
        <nav className="mt-8 space-y-1">
          {navItems.map((item) => {
            const active = isActiveHref(item.href);
            const pending = pendingHref === item.href && !active;
            const highlighted = active || pending;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                data-pending={pending ? "true" : undefined}
                onClick={(event) => handleNavClick(event, item.href)}
                onFocus={() => router.prefetch(item.href)}
                onMouseEnter={() => router.prefetch(item.href)}
                className={`relative flex h-10 items-center gap-3 rounded-md px-3 text-sm transition ${
                  highlighted
                    ? "bg-panel-strong text-foreground"
                    : "text-muted hover:bg-panel hover:text-foreground"
                }`}
              >
                {highlighted && (
                  <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent" />
                )}
                <Icon size={17} />
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
                {pending && (
                  <span
                    aria-hidden="true"
                    className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-muted border-t-accent"
                  />
                )}
              </Link>
            );
          })}
        </nav>
      </aside>

      <header className="sticky top-0 z-10 border-b border-line bg-[#14161b]/95 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between">
          <Link href="/" className="font-semibold">
            SG Data & AI Job Pulse
          </Link>
          <BarChart3 size={20} className="text-accent" />
        </div>
        <nav className="scrollbar-thin mt-3 flex gap-2 overflow-x-auto pb-1">
          {navItems.map((item) => {
            const active = isActiveHref(item.href);
            const pending = pendingHref === item.href && !active;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                onClick={(event) => handleNavClick(event, item.href)}
                onFocus={() => router.prefetch(item.href)}
                onMouseEnter={() => router.prefetch(item.href)}
                className={`inline-flex h-9 shrink-0 items-center gap-2 rounded-md border px-3 text-xs transition ${
                  active || pending
                    ? "border-accent bg-panel-strong text-foreground"
                    : "border-line text-muted"
                }`}
              >
                {item.label}
                {pending && (
                  <span
                    aria-hidden="true"
                    className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-muted border-t-accent"
                  />
                )}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}
