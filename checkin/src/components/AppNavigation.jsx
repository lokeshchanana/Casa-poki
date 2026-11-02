import React from 'react';
import { 
  ClipboardList, 
  MessageSquareCode, 
  BrainCircuit,
  Sun, 
  Moon, 
  Maximize2, 
  Minimize2,
  Sparkles,
  ShieldCheck
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function AppNavigation({ activeTab, setActiveTab, isKioskMode, toggleKioskMode }) {
  const { resolvedTheme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 bg-white/95 dark:bg-charcoal-dark/95 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 transition-colors">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between gap-4">
        
        {/* Brand / Title */}
        <div className="flex items-center gap-3">
          <img 
            src="/loki-profile.jpg" 
            alt="Lokesh Chanana" 
            className="w-9 h-9 rounded-full object-cover object-[50%_25%] border border-neutral-300 dark:border-neutral-700 shadow-sm scale-x-[-1]" 
          />
          <div className="hidden sm:block">
            <h1 className="text-sm font-serif font-bold text-neutral-900 dark:text-neutral-100 leading-tight">
              Lokesh Chanana
            </h1>
            <p className="text-[10px] text-neutral-500 dark:text-neutral-400 font-sans tracking-wider uppercase">
              Field Portal & CRM Hub
            </p>
          </div>
        </div>

        {/* Center Tab Switcher */}
        <div className="flex items-center p-1 bg-neutral-100 dark:bg-charcoal rounded-xl border border-neutral-200/80 dark:border-neutral-800">
          <button
            type="button"
            onClick={() => setActiveTab('checkin')}
            className={`flex items-center gap-2 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'checkin'
                ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
          >
            <ClipboardList className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>Check-In Sheet</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('manager')}
            className={`flex items-center gap-2 px-3.5 sm:px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'manager'
                ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
          >
            <BrainCircuit className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Manager</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Manager + IT + Auditor Active" />
          </button>
        </div>

        {/* Right Action Icons */}
        <div className="flex items-center gap-2">
          {/* Theme Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-lg text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            title={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {resolvedTheme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-neutral-600" />}
          </button>

          {/* Dedicated Kiosk Mode button */}
          {toggleKioskMode && (
            <button
              type="button"
              onClick={toggleKioskMode}
              className={`p-2 rounded-lg text-xs font-bold transition-colors hidden sm:flex items-center gap-1.5 ${
                isKioskMode 
                  ? 'bg-cyan-600 text-white' 
                  : 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 hover:opacity-90'
              }`}
              title={isKioskMode ? 'Exit Kiosk Mode' : 'Enter Kiosk Mode for Open House Visitors'}
            >
              {isKioskMode ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              <span>{isKioskMode ? 'Exit Kiosk' : 'Kiosk'}</span>
            </button>
          )}
        </div>

      </div>
    </header>
  );
}
