import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import AppNavigation from './components/AppNavigation';
import OpenHouseSignIn from './components/OpenHouseSignIn';
import ManagerChat from './components/ManagerChat';
import OfficeFloor from './components/OfficeFloor';
import SocialStudio from './components/SocialStudio';

export default function App() {
  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get('tab');
    if (tabParam === 'manager' || tabParam === 'crm' || tabParam === 'chat') return 'manager';
    if (tabParam === 'office' || tabParam === 'floor') return 'office';
    if (tabParam === 'social' || tabParam === 'studio') return 'social';
    const saved = localStorage.getItem('checkin_active_tab');
    if (saved === 'crm') return 'manager';
    return saved || 'checkin';
  });

  useEffect(() => {
    localStorage.setItem('checkin_active_tab', activeTab);
  }, [activeTab]);

  return (
    <ThemeProvider>
      <div className="min-h-[100dvh] bg-ivory dark:bg-charcoal text-neutral-900 dark:text-neutral-100 flex flex-col font-sans transition-colors duration-300">
        <AppNavigation 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
        />
        
        <main className="flex-1 flex flex-col">
          {activeTab === 'checkin' && (
            <OpenHouseSignIn onOpenCrm={() => setActiveTab('manager')} />
          )}
          {activeTab === 'manager' && (
            <ManagerChat onBackToCheckIn={() => setActiveTab('checkin')} />
          )}
          {activeTab === 'office' && (
            <OfficeFloor onOpenChat={() => setActiveTab('manager')} />
          )}
          {activeTab === 'social' && (
            <SocialStudio />
          )}
        </main>
      </div>
    </ThemeProvider>
  );
}
