import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Header from './components/Header';
import Hero from './components/Hero';
import MicroMarkets from './components/MicroMarkets';
import TechnicalEdge from './components/TechnicalEdge';
import Resources from './components/Resources';
import ContactSection from './components/ContactSection';
import Footer from './components/Footer';
import InstagramReels from './components/InstagramReels';
import SEOHead from './components/SEOHead';
import FAQSection from './components/FAQSection';

// Pages
import BuyersGuide from './pages/BuyersGuide';
import SellersGuide from './pages/SellersGuide';
import InvestorsGuide from './pages/InvestorsGuide';
import CommercialGuide from './pages/CommercialGuide';
import AboutLoki from './pages/AboutLoki';
import OpenHouseSignIn from './pages/OpenHouseSignIn';
import EastsideCore from './pages/markets/EastsideCore';
import SeattleCore from './pages/markets/SeattleCore';
import NorthSound from './pages/markets/NorthSound';
import SouthSound from './pages/markets/SouthSound';
import ThurstonBelt from './pages/markets/ThurstonBelt';
import CityMarketPage from './pages/CityMarketPage';
import { CITY_PAGES_DATA } from './data/cityPagesData';

function Home() {
  return (
    <>
      <Hero />
      <MicroMarkets />
      <TechnicalEdge />
      <Resources />
      <InstagramReels />
      <FAQSection routePath="/" />
      <ContactSection />
    </>
  );
}

function CheckInPortal() {
  useEffect(() => {
    document.title = 'Open House Guest Check-In | Lokesh Chanana (Loki)';
  }, []);

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-ivory dark:bg-charcoal text-charcoal dark:text-silver flex flex-col font-sans selection:bg-silver/30 transition-colors duration-300">
        <main className="flex-1">
          <OpenHouseSignIn />
        </main>
      </div>
    </ThemeProvider>
  );
}

export default function App() {
  const isCheckInHost =
    typeof window !== 'undefined' &&
    (window.location.hostname.toLowerCase().startsWith('checkin.') ||
     window.location.pathname === '/checkin' ||
     window.location.pathname === '/check-in' ||
     new URLSearchParams(window.location.search).has('checkin'));

  if (isCheckInHost) {
    return <CheckInPortal />;
  }

  return (
    <ThemeProvider>
      <BrowserRouter>
        <SEOHead />
        <div className="min-h-screen bg-ivory dark:bg-charcoal text-charcoal dark:text-silver flex flex-col font-sans selection:bg-silver/30 transition-colors duration-300">
          <Header />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/buyers" element={<BuyersGuide />} />
              <Route path="/sellers" element={<SellersGuide />} />
              <Route path="/investors" element={<InvestorsGuide />} />
              <Route path="/commercial" element={<CommercialGuide />} />
              <Route path="/markets/eastside-core" element={<EastsideCore />} />
              <Route path="/markets/seattle-core" element={<SeattleCore />} />
              <Route path="/markets/north-sound" element={<NorthSound />} />
              <Route path="/markets/south-sound" element={<SouthSound />} />
              <Route path="/markets/thurston-belt" element={<ThurstonBelt />} />
              {Object.keys(CITY_PAGES_DATA).map((slug) => (
                <Route
                  key={slug}
                  path={`/cities/${slug}`}
                  element={<CityMarketPage citySlug={slug} />}
                />
              ))}
              <Route path="/about" element={<AboutLoki />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}
