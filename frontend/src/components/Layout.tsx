import { NavLink, Outlet } from "react-router-dom";

const tabs = [
  { to: "/", label: "Overview" },
  { to: "/explorer", label: "Forecast Explorer" },
  { to: "/accuracy", label: "Accuracy Analysis" },
  { to: "/revisions", label: "Revisions" },
  { to: "/methodology", label: "Methodology" },
];

export default function Layout() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-slate-900">
                UK Wind — Day-Ahead Decision Support
              </h1>
              <p className="text-xs text-slate-500">
                National wind forecast & accuracy · Elexon BMRS · January 2026 delivery days
              </p>
            </div>
            <nav aria-label="Main navigation" className="flex flex-wrap gap-1">
              {tabs.map((t) => (
                <NavLink
                  key={t.to}
                  to={t.to}
                  end={t.to === "/"}
                  className={({ isActive }) =>
                    "rounded-md px-3 py-2 text-sm font-medium " +
                    (isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900")
                  }
                >
                  {t.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        Data: Elexon BMRS (FUELHH, WINDFOR) · Times shown in Europe/London (UTC in winter, same as GMT for January) ·
        Snapshot committed at build time
      </footer>
    </div>
  );
}
