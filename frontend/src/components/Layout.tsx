import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";

import {
  ChartIcon,
  ChatIcon,
  FileIcon,
  FolderIcon,
  HomeIcon,
  LogOutIcon,
  MenuIcon,
  SparkleIcon,
  XIcon,
} from "./icons";

import { LocaleSwitcher } from "./LocaleSwitcher";
import { Logo } from "./Logo";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function Layout() {
  const { user, logout } = useAuth();
  const { t, locale } = useI18n();

  const [isMobileMenuOpen, setIsMobileMenuOpen] =
    useState(false);

  const labels =
    locale === "tr"
      ? {
          intelligence: "INTELLIGENCE",
          knowledge: "KNOWLEDGE",
          commandCenter: "Komuta Merkezi",
          ask: "Masteacon'a Sor",
          agent: "AI Ajanı",
          library: "Bilgi Kütüphanesi",
          workspaces: "Çalışma Alanları",
          observability: "Gözlemlenebilirlik",
          account: "KNOWLEDGE ACCOUNT",
          openMenu: "Menüyü aç",
          closeMenu: "Menüyü kapat",
        }
      : {
          intelligence: "INTELLIGENCE",
          knowledge: "KNOWLEDGE",
          commandCenter: "Command Center",
          ask: "Ask Masteacon",
          agent: "AI Agent",
          library: "Knowledge Library",
          workspaces: "Workspaces",
          observability: "Observability",
          account: "KNOWLEDGE ACCOUNT",
          openMenu: "Open menu",
          closeMenu: "Close menu",
        };

  function closeMobileMenu() {
    setIsMobileMenuOpen(false);
  }

  return (
    <div className="app-shell">
      <header className="mobile-app-header">
        <Logo size={34} withWordmark />

        <button
          type="button"
          className="mobile-menu-trigger"
          aria-label={
            isMobileMenuOpen
              ? labels.closeMenu
              : labels.openMenu
          }
          aria-expanded={isMobileMenuOpen}
          onClick={() =>
            setIsMobileMenuOpen((open) => !open)
          }
        >
          {isMobileMenuOpen ? (
            <XIcon width={18} height={18} />
          ) : (
            <MenuIcon width={18} height={18} />
          )}
        </button>
      </header>

      {isMobileMenuOpen && (
        <button
          type="button"
          className="mobile-sidebar-backdrop"
          aria-label={labels.closeMenu}
          onClick={closeMobileMenu}
        />
      )}

      <aside
        className={
          isMobileMenuOpen
            ? "sidebar sidebar-mobile-open"
            : "sidebar"
        }
      >
        <div className="sidebar-mobile-heading">
          <Logo size={40} withWordmark />

          <button
            type="button"
            onClick={closeMobileMenu}
            aria-label={labels.closeMenu}
          >
            <XIcon width={18} height={18} />
          </button>
        </div>

        <div className="sidebar-brand">
          <Logo size={58} withWordmark />

          <span className="sidebar-brand-tagline">
            Your beacon to mastery
          </span>
        </div>

        <WorkspaceSwitcher />

        <div className="sidebar-section">
          <span className="sidebar-section-label">
            {labels.intelligence}
          </span>

          <nav className="sidebar-nav">
            <NavLink
              to="/overview"
              className={({ isActive }) =>
                isActive ? "active" : ""
              }
              onClick={closeMobileMenu}
            >
              <HomeIcon />
              <span>{labels.commandCenter}</span>
            </NavLink>

            <NavLink
              to="/chat"
              className={({ isActive }) =>
                isActive ? "active" : ""
              }
              onClick={closeMobileMenu}
            >
              <ChatIcon />
              <span>{labels.ask}</span>
            </NavLink>

            <NavLink
              to="/agent"
              className={({ isActive }) =>
                isActive ? "active" : ""
              }
              onClick={closeMobileMenu}
            >
              <SparkleIcon />
              <span>{labels.agent}</span>
            </NavLink>
          </nav>
        </div>

        <div className="sidebar-section">
          <span className="sidebar-section-label">
            {labels.knowledge}
          </span>

          <nav className="sidebar-nav">
            <NavLink
              to="/documents"
              className={({ isActive }) =>
                isActive ? "active" : ""
              }
              onClick={closeMobileMenu}
            >
              <FileIcon />
              <span>{labels.library}</span>
            </NavLink>

            <NavLink
              to="/workspaces"
              className={({ isActive }) =>
                isActive ? "active" : ""
              }
              onClick={closeMobileMenu}
            >
              <FolderIcon />
              <span>{labels.workspaces}</span>
            </NavLink>

            <NavLink
              to="/observability"
              className={({ isActive }) =>
                isActive ? "active" : ""
              }
              onClick={closeMobileMenu}
            >
              <ChartIcon />
              <span>{labels.observability}</span>
            </NavLink>
          </nav>
        </div>

        <div className="sidebar-footer">
          <span className="sidebar-section-label">
            {labels.account}
          </span>

          <div className="sidebar-account">
            <span className="sidebar-account-avatar">
              {(user?.email || "M")
                .charAt(0)
                .toUpperCase()}
            </span>

            <div className="sidebar-account-copy">
              <strong>Masteacon User</strong>
              <span>{user?.email}</span>
            </div>
          </div>

          <div className="sidebar-controls">
            <ThemeSwitcher />
            <LocaleSwitcher />
          </div>

          <button
            className="btn btn-secondary btn-sm sidebar-logout"
            onClick={logout}
          >
            <LogOutIcon width={15} height={15} />
            {t("nav.logout")}
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
