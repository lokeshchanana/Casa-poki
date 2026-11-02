
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X, Phone, Mail, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { SocialIconRow } from './SocialLinks';

export default function Header() {
  const { theme, resolvedTheme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const [marketsOpen, setMarketsOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={"fixed w-full top-0 z-50 transition-all duration-500 " + (isScrolled ? "bg-white/95 dark:bg-charcoal-dark/95 backdrop-blur-md border-b border-silver/20 py-1" : "bg-transparent border-transparent py-3")}>
      {/* Mobile Top Bar */}
      <div className="md:hidden bg-charcoal dark:bg-black text-ivory dark:text-silver text-xs py-2 px-4 flex justify-between items-center border-b border-silver/20">
        <a href="tel:8018601052" className="flex items-center gap-2"><Phone className="w-3 h-3"/> (801) 860-1052</a>
        <a href="mailto:lokeshchanana@outlook.com" className="flex items-center gap-2"><Mail className="w-3 h-3"/> Email</a>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-1 md:py-2">
          
          <Link to="/" className="flex items-center gap-4 group">
            <img src="/lc-logo.png" alt="Lc Logo" className="h-16 md:h-20 w-auto object-contain opacity-90 transition-transform group-hover:scale-105" />
            <div className="hidden sm:block">
              <h1 className="font-serif font-bold text-lg text-charcoal dark:text-silver uppercase tracking-widest leading-none">Lokesh Chanana</h1>
              <p className="text-[10px] font-sans text-charcoal-light dark:text-silver-dark uppercase tracking-widest mt-1">Real Estate Agent</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            <Link to="/" className="text-xs font-bold uppercase tracking-widest text-charcoal-light hover:text-charcoal dark:text-silver-dark dark:hover:text-silver transition-colors">Home</Link>
            
            <div 
              className="relative"
              onMouseEnter={() => setResourcesOpen(true)}
              onMouseLeave={() => setResourcesOpen(false)}
            >
              <button className="text-xs font-bold uppercase tracking-widest text-charcoal-light hover:text-charcoal dark:text-silver-dark dark:hover:text-silver transition-colors py-2">
                Resources
              </button>
              {resourcesOpen && (
                <div className="absolute top-full right-0 w-48 bg-white dark:bg-charcoal-dark border border-silver/20 shadow-xl py-2">
                  <Link to="/buyers" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Buyer's Guide</Link>
                  <Link to="/sellers" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Seller's Guide</Link>
                  <Link to="/investors" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Investor's Guide</Link>
                  <Link to="/commercial" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Commercial</Link>
                </div>
              )}
            </div>

            <div 
              className="relative"
              onMouseEnter={() => setMarketsOpen(true)}
              onMouseLeave={() => setMarketsOpen(false)}
            >
              <button className="text-xs font-bold uppercase tracking-widest text-charcoal-light hover:text-charcoal dark:text-silver-dark dark:hover:text-silver transition-colors py-2">
                Markets
              </button>
              {marketsOpen && (
                <div className="absolute top-full right-0 w-48 bg-white dark:bg-charcoal-dark border border-silver/20 shadow-xl py-2">
                  <Link to="/markets/eastside-core" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Eastside Tech Core</Link>
                  <Link to="/markets/seattle-core" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Seattle Urban Core</Link>
                  <Link to="/markets/north-sound" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">North Sound Corridor</Link>
                  <Link to="/markets/south-sound" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">South Sound Hub</Link>
                  <Link to="/markets/thurston-belt" className="block px-4 py-2 text-xs uppercase tracking-widest text-charcoal dark:text-silver hover:bg-ivory dark:hover:bg-charcoal">Capital & Exurban Fringe</Link>
                </div>
              )}
            </div>

            <Link to="/about" className="text-xs font-bold uppercase tracking-widest text-charcoal-light hover:text-charcoal dark:text-silver-dark dark:hover:text-silver transition-colors">About Loki</Link>

            {/* Desktop Theme Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
              title={`Theme: ${theme === 'system' ? 'Device mode (' + resolvedTheme + ')' : resolvedTheme}. Click to toggle.`}
              className="p-2 border border-silver/40 dark:border-silver/20 hover:border-charcoal dark:hover:border-silver hover:bg-black/5 dark:hover:bg-white/10 transition-colors text-charcoal dark:text-silver flex items-center justify-center rounded-sm"
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-slate-700" />
              )}
            </button>

            {/* Desktop Social Profiles */}
            <div className="hidden lg:flex items-center pl-3 border-l border-silver/30 dark:border-silver/20">
              <SocialIconRow size="sm" />
            </div>
          </nav>

          {/* Mobile Right Controls: Theme Toggle & Hamburger */}
          <div className="md:hidden flex items-center gap-2">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
              className="p-2 border border-silver/40 dark:border-silver/20 text-charcoal dark:text-silver rounded-sm"
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-slate-700" />
              )}
            </button>

            <button 
              className="p-2 text-charcoal dark:text-silver border border-silver/40 dark:border-silver/20 rounded-sm"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-charcoal-dark border-t border-silver/20 absolute w-full left-0 shadow-2xl">
          <div className="px-4 py-6 space-y-6">
            <Link to="/" onClick={() => setMobileMenuOpen(false)} className="block text-sm font-bold uppercase tracking-widest text-charcoal dark:text-silver">Home</Link>
            
            <div className="border-t border-silver/20 pt-4">
              <p className="text-xs font-bold uppercase tracking-widest text-silver-dark mb-4">Resources</p>
              <div className="space-y-4 pl-4">
                <Link to="/buyers" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Buyer's Guide</Link>
                <Link to="/sellers" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Seller's Guide</Link>
                <Link to="/investors" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Investor's Guide</Link>
                <Link to="/commercial" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Commercial</Link>
              </div>
            </div>
            
            <div className="border-t border-silver/20 pt-4">
              <p className="text-xs font-bold uppercase tracking-widest text-silver-dark mb-4">Markets</p>
              <div className="space-y-4 pl-4">
                <Link to="/markets/eastside-core" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Eastside Tech Core</Link>
                <Link to="/markets/seattle-core" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Seattle Urban Core</Link>
                <Link to="/markets/north-sound" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">North Sound Corridor</Link>
                <Link to="/markets/south-sound" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">South Sound Hub</Link>
                <Link to="/markets/thurston-belt" onClick={() => setMobileMenuOpen(false)} className="block text-xs uppercase tracking-widest text-charcoal dark:text-silver">Capital & Exurban Fringe</Link>
              </div>
            </div>

            <Link to="/about" onClick={() => setMobileMenuOpen(false)} className="block text-sm font-bold uppercase tracking-widest text-charcoal dark:text-silver border-t border-silver/20 pt-4">About Loki</Link>

            {/* Mobile Drawer Theme Row */}
            <div className="border-t border-silver/20 pt-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-charcoal dark:text-silver">Theme</p>
                <p className="text-[10px] text-silver-dark font-sans">
                  {theme === 'system' ? 'Device Mode' : (resolvedTheme === 'dark' ? 'Dark Mode' : 'Light Mode')}
                </p>
              </div>
              <button
                type="button"
                onClick={toggleTheme}
                className="flex items-center gap-2 px-3 py-1.5 border border-silver/40 dark:border-silver/20 text-xs font-bold uppercase tracking-wider text-charcoal dark:text-silver rounded-sm hover:border-charcoal dark:hover:border-silver"
              >
                {resolvedTheme === 'dark' ? (
                  <>
                    <Sun className="w-3.5 h-3.5 text-amber-400" />
                    <span>Light Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-3.5 h-3.5 text-slate-700" />
                    <span>Dark Mode</span>
                  </>
                )}
              </button>
            </div>

            {/* Mobile Drawer Social Links */}
            <div className="border-t border-silver/20 pt-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-charcoal dark:text-silver">Connect</p>
                <p className="text-[10px] text-silver-dark font-sans">Reviews & Social</p>
              </div>
              <SocialIconRow size="sm" />
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
