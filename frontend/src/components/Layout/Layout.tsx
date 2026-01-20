import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/saas', label: 'SaaS Products', icon: '🚀' },
    { path: '/submissions', label: 'Submissions', icon: '📝' },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-[#0d1117]">
      {/* Sidebar Navigation */}
      <aside className="fixed left-0 top-0 h-screen w-64 bg-[#161b22] border-r border-[#30363d] p-6 z-10">
        <div className="mb-8 animate-fade-in">
          <h1 className="text-2xl font-bold text-white mb-1">GENIE OPS</h1>
          <p className="text-sm text-[#8b949e]">Automated Submissions</p>
        </div>

        <nav className="space-y-2">
          {navItems.map((item, index) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 ${
                isActive(item.path)
                  ? 'bg-[#58a6ff] text-white shadow-lg shadow-blue-500/20'
                  : 'text-[#8b949e] hover:bg-[#30363d] hover:text-[#c9d1d9]'
              }`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8 animate-fade-in">
        {children}
      </main>
    </div>
  );
}
