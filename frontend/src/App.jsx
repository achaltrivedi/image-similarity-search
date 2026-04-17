// React
import { useLocation, Link, NavLink } from 'react-router';

// App components
import { ModeToggle } from '@/components/ModeToggle';

// Pages
import Home from '@/pages/Home';
import Data from '@/pages/Data';
import Settings from '@/pages/Settings';

function App() {
  const location = useLocation();

  const navLinkClass = ({ isActive }) =>
    `transition-colors hover:text-foreground ${isActive ? 'text-primary font-semibold' : 'text-muted-foreground'}`;

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Shared Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-3">
                <div>
                  <h1 className="text-lg font-semibold tracking-tight text-foreground">
                    Image Similarity Search
                  </h1>
                </div>
              </Link>
              <nav className="flex items-center gap-4 text-sm font-medium">
                <NavLink to="/" className={navLinkClass}>
                  Home
                </NavLink>
                <NavLink to="/data" className={navLinkClass}>
                  Data
                </NavLink>
                <NavLink to="/settings" className={navLinkClass}>
                  Settings
                </NavLink>
              </nav>
            </div>
            <div className="flex items-center gap-2">
              <ModeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content — both pages stay mounted, visibility toggled via CSS */}
      <main>
        <div style={{ display: location.pathname === '/' ? 'block' : 'none' }}>
          <Home />
        </div>
        <div style={{ display: location.pathname === '/data' ? 'block' : 'none' }}>
          <Data />
        </div>
        <div style={{ display: location.pathname === '/settings' ? 'block' : 'none' }}>
          <Settings />
        </div>
      </main>
    </div>
  );
}

export default App;
