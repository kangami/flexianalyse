import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

interface NavDropdownItem {
  label: string;
  description?: string;
}

interface NavItem {
  label: string;
  hasDropdown?: boolean;
  dropdownItems?: NavDropdownItem[];
}

const navItems: NavItem[] = [
  {
    label: 'Platform',
    hasDropdown: true,
    dropdownItems: [
      { label: 'AI-Powered Analysis', description: 'Document understanding & data extraction' },
      { label: 'Unified Knowledge Layer', description: 'Connect all your enterprise data' },
      { label: 'AI Agent Workforce', description: 'Autonomous agents that execute tasks' },
      { label: 'Insights & Intelligence', description: 'Risk detection, bottlenecks & trends' },
    ],
  },
  {
    label: 'Solutions',
    hasDropdown: true,
    dropdownItems: [
      { label: 'Contract Management', description: 'Automate contract lifecycle' },
      { label: 'Invoice Processing', description: 'Streamline AP workflows' },
      { label: 'Employee Onboarding', description: 'Accelerate HR processes' },
      { label: 'Vendor Management', description: 'Centralize vendor operations' },
    ],
  },
  { label: 'Customer Stories' },
  { label: 'Resources' },
  { label: 'Company' },
  { label: 'Blog' },
];

const Navbar: React.FC = () => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const navRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleDropdown = (label: string) => {
    setOpenDropdown(openDropdown === label ? null : label);
  };

  return (
    <nav className="fixed top-0 w-full bg-white/95 backdrop-blur-md border-b border-gray-100 z-50" ref={navRef}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse Logo" className="w-9 h-9 object-contain" />
            <span className="text-xl font-bold text-gray-900 tracking-tight">FlexiAnalyse</span>
          </div>

          {/* Center Nav Links */}
          <div className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => (
              <div key={item.label} className="relative">
                <button
                  onClick={() => item.hasDropdown && toggleDropdown(item.label)}
                  onMouseEnter={() => item.hasDropdown && setOpenDropdown(item.label)}
                  className={`flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    openDropdown === item.label
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
                  }`}
                >
                  {item.label}
                  {item.hasDropdown && (
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openDropdown === item.label ? 'rotate-180' : ''}`} />
                  )}
                </button>

                {/* Dropdown */}
                {item.hasDropdown && openDropdown === item.label && (
                  <div
                    onMouseLeave={() => setOpenDropdown(null)}
                    className="absolute top-full left-0 mt-1 w-72 bg-white rounded-xl shadow-xl border border-gray-100 py-2 animate-fadeIn"
                  >
                    {item.dropdownItems?.map((dropItem) => (
                      <a
                        key={dropItem.label}
                        href="#"
                        className="block px-4 py-3 hover:bg-blue-50 transition-colors"
                      >
                        <span className="block text-sm font-medium text-gray-900">{dropItem.label}</span>
                        {dropItem.description && (
                          <span className="block text-xs text-gray-500 mt-0.5">{dropItem.description}</span>
                        )}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Book a Demo Button */}
          <div className="flex items-center">
            <button className="relative px-5 py-2 text-sm font-semibold rounded-full border-2 border-transparent bg-clip-padding transition-all duration-200 hover:scale-105 hover:shadow-lg"
              style={{
                backgroundImage: 'linear-gradient(white, white), linear-gradient(-45deg, #3b82f6, #8b5cf6, #ec4899, #f59e0b, #10b981)',
                backgroundOrigin: 'border-box',
                backgroundClip: 'padding-box, border-box',
                backgroundSize: '100% 100%, 400% 400%',
                animation: 'gradientFlow 3s ease-in-out infinite',
              }}
            >
              <span className="font-bold text-blue-800">Get Started</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
