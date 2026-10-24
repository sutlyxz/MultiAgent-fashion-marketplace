import { useState, useEffect } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useMarketplace } from "../features/marketplace/MarketplaceContext";

export function SiteLayout() {
  const { cartCount, user, signOut } = useMarketplace();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-paper text-ink flex flex-col">
      {/* Announcement Bar: ~44px tall on desktop, charcoal-black */}
      <div className="min-h-11 py-2 bg-[#1e1f1c] text-[#F6F3ED] px-4 flex items-center justify-center text-[10px] sm:text-xs tracking-[0.15em] sm:tracking-[0.18em] uppercase font-light text-center leading-normal">
        A little more considered, a little less ordinary
      </div>

      {/* Main Navigation: ~74px tall on desktop, warm ivory (#F6F3ED) */}
      <header className="border-b border-borderIvory bg-paper/95 backdrop-blur-sm sticky top-0 z-30 transition-shadow">
        <div className="mx-auto flex h-[74px] max-w-7xl items-center justify-between gap-3 sm:gap-6 px-4 sm:px-8">
          {/* Brand Wordmark aligned to far left */}
          <Link
            className="font-display text-2xl sm:text-3xl font-medium tracking-[0.2em] sm:tracking-[0.24em] uppercase text-ink transition-opacity hover:opacity-85 shrink-0"
            to="/"
          >
            CLOTHIFY
          </Link>

          {/* Centered navigation links */}
          <nav aria-label="Main navigation" className="hidden items-center gap-8 md:flex">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `nav-link ${isActive ? "text-ink font-semibold" : ""}`}
            >
              Home
            </NavLink>
            <NavLink
              to="/products"
              className={({ isActive }) => `nav-link ${isActive ? "text-ink font-semibold" : ""}`}
            >
              Shop
            </NavLink>
            <NavLink
              to="/account/orders"
              className={({ isActive }) => `nav-link ${isActive ? "text-ink font-semibold" : ""}`}
            >
              My orders
            </NavLink>
            <NavLink
              to="/account/profile"
              className={({ isActive }) => `nav-link ${isActive ? "text-ink font-semibold" : ""}`}
            >
              Profile
            </NavLink>
            {user?.role === "seller" && (
              <NavLink
                to="/seller/products"
                className={({ isActive }) =>
                  `nav-link ${isActive ? "text-ink font-semibold" : ""}`
                }
              >
                Seller Studio
              </NavLink>
            )}
          </nav>

          {/* Right controls: Account, Bag and Hamburger for Mobile */}
          <div className="flex items-center gap-3 sm:gap-5 text-xs">
            <Link
              to="/products"
              aria-label="Search collection"
              className="hidden text-ink/70 hover:text-ink sm:flex items-center gap-1.5 transition"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </Link>
            {user ? (
              <button
                className="hidden font-sans text-xs uppercase tracking-[0.14em] text-ink/75 hover:text-ink sm:block transition"
                onClick={() => {
                  signOut();
                  navigate("/");
                }}
                type="button"
              >
                Sign out
              </button>
            ) : (
              <Link
                className="hidden font-sans text-xs uppercase tracking-[0.14em] text-ink/75 hover:text-ink sm:block transition"
                to="/login"
              >
                Sign in
              </Link>
            )}
            <Link
              aria-label={`Shopping bag, ${cartCount} items`}
              className="flex items-center gap-1.5 sm:gap-2 font-sans text-xs uppercase tracking-[0.16em] text-ink hover:opacity-80 transition"
              to="/cart"
            >
              <span>Bag</span>
              <span className="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full bg-ink text-[#F6F3ED] text-[10px] font-medium">
                {cartCount}
              </span>
            </Link>

            {/* Mobile Hamburger Toggle Button */}
            <button
              type="button"
              id="mobile-menu-toggle"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="md:hidden p-1.5 text-ink hover:opacity-75 focus:outline-none transition-colors"
            >
              {mobileMenuOpen ? (
                <svg className="w-5 h-5 stroke-current" fill="none" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5 stroke-current" fill="none" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <nav
            aria-label="Mobile navigation"
            className="border-t border-borderIvory bg-paper/98 px-5 py-4 md:hidden flex flex-col space-y-1 shadow-lg backdrop-blur-md"
          >
            <NavLink
              to="/"
              end
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] transition-colors ${
                  isActive ? "bg-ink text-paper font-semibold" : "text-ink/80 hover:bg-ink/5"
                }`
              }
            >
              Home
            </NavLink>
            <NavLink
              to="/products"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] transition-colors ${
                  isActive ? "bg-ink text-paper font-semibold" : "text-ink/80 hover:bg-ink/5"
                }`
              }
            >
              Shop
            </NavLink>
            <NavLink
              to="/account/orders"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] transition-colors ${
                  isActive ? "bg-ink text-paper font-semibold" : "text-ink/80 hover:bg-ink/5"
                }`
              }
            >
              My Orders
            </NavLink>
            <NavLink
              to="/account/profile"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] transition-colors ${
                  isActive ? "bg-ink text-paper font-semibold" : "text-ink/80 hover:bg-ink/5"
                }`
              }
            >
              Profile
            </NavLink>
            {user?.role === "seller" && (
              <NavLink
                to="/seller/products"
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] transition-colors ${
                    isActive ? "bg-ink text-paper font-semibold" : "text-ink/80 hover:bg-ink/5"
                  }`
                }
              >
                Seller Studio
              </NavLink>
            )}

            <div className="pt-3 border-t border-borderIvory/70 mt-2 flex flex-col gap-2">
              <Link
                to="/cart"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] text-ink/80 hover:bg-ink/5 flex items-center justify-between"
              >
                <span>Shopping Bag</span>
                <span className="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full bg-ink text-[#F6F3ED] text-[10px] font-medium">
                  {cartCount}
                </span>
              </Link>
              {user ? (
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    signOut();
                    navigate("/");
                  }}
                  className="w-full text-left px-3 py-2.5 rounded font-sans text-xs uppercase tracking-[0.18em] text-red-700 hover:bg-red-50 transition-colors"
                >
                  Sign Out
                </button>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="button-primary text-xs w-full text-center mt-1 py-3"
                >
                  Sign In
                </Link>
              )}
            </div>
          </nav>
        )}
      </header>

      {/* Main content: flexible container allowing full width for hero / benefits */}
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>

      {/* Minimal Copyright Footer for all pages */}
      <footer className="mt-auto border-t border-[#DDD8CE] bg-[#F6F3ED] px-5 py-6 text-center text-xs text-[#77766F]">
        <p>© 2026 Clothify. All rights reserved.</p>
      </footer>
    </div>
  );
}
