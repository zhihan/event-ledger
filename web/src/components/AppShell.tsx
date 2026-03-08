import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";

export function AppShell() {
  return (
    <>
      <NavBar />
      <main className="main-content">
        <Outlet />
      </main>
    </>
  );
}
