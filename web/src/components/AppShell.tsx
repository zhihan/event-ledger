import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";

export function AppShell() {
  return (
    <div className="app-shell">
      <NavBar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
