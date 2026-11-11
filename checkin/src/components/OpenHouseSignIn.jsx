import React, { useState, useEffect, useRef } from 'react';
import { 
  Phone, 
  Mail, 
  CheckCircle2, 
  Printer, 
  Maximize2, 
  Minimize2, 
  Settings, 
  UserCheck, 
  Users, 
  MapPin, 
  Sparkles, 
  RotateCcw,
  Navigation,
  Sun,
  Moon,
  Search,
  X,
  Check,
  ShieldCheck,
  Compass,
  Info,
  Bot,
  MessageSquareCode
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { WA_COUNTIES_MARKETS, ALL_CITIES, findNearestMarket } from '../data/waMarkets';

const NEED_OPTIONS = [
  { id: 'buy_now', label: 'Looking to buy now', icon: '🏡', desc: 'Actively searching for a home' },
  { id: 'browsing', label: 'Just browsing / open house tour', icon: '👀', desc: 'Exploring neighborhoods & designs' },
  { id: 'buy_year', label: 'Plan to buy within a year', icon: '⏳', desc: 'Timeline is 3 to 12 months out' },
  { id: 'selling', label: 'Interested in selling a home', icon: '🏷️', desc: 'Curious about home valuation & market' }
];

export default function OpenHouseSignIn({ onOpenCrm }) {
  const { resolvedTheme, toggleTheme } = useTheme();

  // Config State
  const [marketCity, setMarketCity] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('city') || params.get('market') || localStorage.getItem('oh_market_city') || 'Auburn';
  });
  const [propertyAddress, setPropertyAddress] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('property') || params.get('address') || localStorage.getItem('oh_property_address') || '';
  });
  const [showConfig, setShowConfig] = useState(false);
  const [viewMode, setViewMode] = useState('digital'); // 'digital' or 'print'
  const [showRoster, setShowRoster] = useState(false);

  // Kiosk Mode State (In-Page dedicated overlay that never closes on typing)
  const [isKioskMode, setIsKioskMode] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('kiosk') === 'true' || sessionStorage.getItem('oh_kiosk_mode') === 'true';
  });
  const [showExitKioskModal, setShowExitKioskModal] = useState(false);

  // GPS Geolocation State
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsMessage, setGpsMessage] = useState(null);

  // Form State
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [feedback, setFeedback] = useState('');
  const [workingWithAgent, setWorkingWithAgent] = useState('No');
  const [agentName, setAgentName] = useState('');
  const [selectedNeeds, setSelectedNeeds] = useState([]);

  // Submission State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedData, setSubmittedData] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [countdown, setCountdown] = useState(6);

  // City Search Filter within settings drawer
  const [citySearch, setCitySearch] = useState('');

  // Form container ref for scroll adjustments
  const formTopRef = useRef(null);

  // Session Sign-In Roster (persisted in localStorage)
  const [roster, setRoster] = useState(() => {
    try {
      const saved = localStorage.getItem('oh_sign_in_roster');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  // Save config changes
  useEffect(() => {
    localStorage.setItem('oh_market_city', marketCity);
  }, [marketCity]);

  useEffect(() => {
    localStorage.setItem('oh_property_address', propertyAddress);
  }, [propertyAddress]);

  useEffect(() => {
    sessionStorage.setItem('oh_kiosk_mode', isKioskMode ? 'true' : 'false');
  }, [isKioskMode]);

  // Auto reset countdown after successful submission
  useEffect(() => {
    let timer;
    if (submittedData && countdown > 0) {
      timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    } else if (submittedData && countdown === 0) {
      resetForm();
    }
    return () => clearTimeout(timer);
  }, [submittedData, countdown]);

  const toggleNeed = (needLabel) => {
    setSelectedNeeds(prev => 
      prev.includes(needLabel) 
        ? prev.filter(n => n !== needLabel)
        : [...prev, needLabel]
    );
  };

  const resetForm = () => {
    setName('');
    setPhone('');
    setEmail('');
    setFeedback('');
    setWorkingWithAgent('No');
    setAgentName('');
    setSelectedNeeds([]);
    setSubmittedData(null);
    setSubmitError(null);
    setCountdown(6);

    if (formTopRef.current) {
      formTopRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Generate 1-tap pre-drafted SMS URL for guests
  const getDraftSmsUrl = (entry) => {
    if (!entry.phone) return null;
    const digits = entry.phone.replace(/[^0-9+]/g, '');
    const cleanPhone = digits.startsWith('+') ? digits : (digits.length === 10 ? `+1${digits}` : digits);
    const guestName = (entry.name || '').trim();
    const isRepresented = entry.workingWithAgent === 'Yes';
    const marketName = (entry.market || marketCity || '').trim();
    const location = marketName ? `${marketName} open house` : "today's open house";

    let body = '';
    if (isRepresented) {
      body = `Hi ${guestName}, this is Lokesh Chanana (Loki). Thank you for touring the ${location} today!\n\nDropping my direct contact card and property details for your records:\nhttps://lokeshchanana.com/loki.vcf\n\nPlease feel free to have your agent reach out to me directly if they need disclosure packets or offer guidelines. Enjoy the rest of your tour!`;
    } else {
      body = `Hi ${guestName}, this is Lokesh Chanana (Loki). Great meeting you at today's ${location}!\n\nDropping my direct contact card so you have all my info saved in your inbox:\nhttps://lokeshchanana.com/loki.vcf\n\nFeel free to text or call me anytime if you have questions about this home, neighborhood comps, or other properties in the area!`;
    }

    return `sms:${cleanPhone}?body=${encodeURIComponent(body)}`;
  };

  // Dedicated phone formatter ensuring numeric keypad input formats smoothly
  const handlePhoneChange = (e) => {
    if (submitError) setSubmitError(null);
    const value = e.target.value;
    if (value.length < phone.length) {
      setPhone(value);
      return;
    }
    let digits = value.replace(/\D/g, '');
    if (digits.length === 11 && digits.startsWith('1')) {
      digits = digits.slice(1);
    }
    if (digits.length === 0) {
      setPhone('');
    } else if (digits.length <= 3) {
      setPhone(`(${digits}`);
    } else if (digits.length <= 6) {
      setPhone(`(${digits.slice(0, 3)}) ${digits.slice(3)}`);
    } else {
      setPhone(`(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`);
    }
  };

  // Toggle Dedicated Kiosk Mode
  const toggleKioskMode = () => {
    if (!isKioskMode) {
      setIsKioskMode(true);
      setShowConfig(false);
      // Attempt HTML5 fullscreen for devices that support it, but state remains true regardless
      if (document.documentElement.requestFullscreen && !document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    } else {
      setShowExitKioskModal(true);
    }
  };

  const confirmExitKiosk = () => {
    setIsKioskMode(false);
    setShowExitKioskModal(false);
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  };

  // GPS Nearest City Calculation
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setGpsMessage({ type: 'error', text: 'Geolocation is not supported by your browser.' });
      return;
    }

    setGpsLoading(true);
    setGpsMessage(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGpsLoading(false);
        const { latitude, longitude } = position.coords;
        const nearest = findNearestMarket(latitude, longitude);

        if (nearest) {
          setMarketCity(nearest.name);
          setGpsMessage({
            type: 'success',
            text: `📍 Detected: ${nearest.name} (~${nearest.distanceMiles} mi away, ${nearest.county})`
          });
        } else {
          setGpsMessage({ type: 'error', text: 'Could not determine nearest city in Puget Sound.' });
        }
      },
      (error) => {
        setGpsLoading(false);
        let msg = 'Unable to retrieve location.';
        if (error.code === error.PERMISSION_DENIED) {
          msg = 'Location access was denied. Please select your city from the list.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          msg = 'Location signal is unavailable.';
        } else if (error.code === error.TIMEOUT) {
          msg = 'Location request timed out. Please try again.';
        }
        setGpsMessage({ type: 'error', text: msg });
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    const cleanPhoneDigits = phone.replace(/\D/g, '');
    const cleanEmail = email.trim();

    if (!cleanPhoneDigits && !cleanEmail) {
      setSubmitError('Please provide at least a phone number or an email address to check in.');
      if (formTopRef.current) {
        formTopRef.current.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    if (cleanPhoneDigits && cleanPhoneDigits.length < 10 && !cleanEmail) {
      setSubmitError('Please enter a valid 10-digit phone number, or provide an email address.');
      if (formTopRef.current) {
        formTopRef.current.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    const payload = {
      name: name.trim(),
      phone: phone.trim(),
      email: email.trim().toLowerCase(),
      feedback: feedback.trim(),
      working_with_agent: workingWithAgent,
      agent_name: workingWithAgent === 'Yes' ? agentName.trim() : '',
      current_needs: selectedNeeds,
      city: marketCity.trim(),
      market: marketCity.trim(),
      lead_source: 'Open House',
      property_address: propertyAddress.trim(),
      submitted_at: new Date().toISOString()
    };

    try {
      const webhookUrl = 'https://n8n.lokeshchanana.com/webhook/open-house-sign-in';
      const res = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json().catch(() => ({ success: res.ok }));

      if (res.ok && data.success !== false) {
        const displayName = data.name || payload.name;
        const isReturning = data.status === 'existing_contact_updated';
        const welcomeMessage = isReturning 
          ? `Welcome back, ${displayName}!` 
          : (data.message || `Welcome, ${displayName}!`);

        const newEntry = {
          id: data.personId || Date.now().toString(),
          name: displayName,
          phone: payload.phone,
          email: payload.email,
          feedback: payload.feedback,
          workingWithAgent: payload.working_with_agent,
          needs: payload.current_needs,
          market: payload.city,
          property: payload.property_address,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        const updatedRoster = [newEntry, ...roster];
        setRoster(updatedRoster);
        localStorage.setItem('oh_sign_in_roster', JSON.stringify(updatedRoster));

        setSubmittedData({
          name: displayName,
          market: payload.city,
          status: data.status || 'created',
          isReturning: isReturning,
          message: welcomeMessage
        });
        setCountdown(6);
      } else {
        setSubmitError(data.message || data.error || 'Unable to record sign-in. Please try again.');
      }
    } catch (err) {
      console.error('Submission error:', err);
      const newEntry = {
        id: 'local-' + Date.now(),
        name: payload.name,
        phone: payload.phone,
        email: payload.email,
        feedback: payload.feedback,
        workingWithAgent: payload.working_with_agent,
        needs: payload.current_needs,
        market: payload.city,
        property: payload.property_address,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      const updatedRoster = [newEntry, ...roster];
      setRoster(updatedRoster);
      localStorage.setItem('oh_sign_in_roster', JSON.stringify(updatedRoster));

      setSubmittedData({
        name: payload.name,
        market: payload.city,
        status: 'saved_locally',
        message: `Welcome, ${payload.name}! Your sign-in has been noted.`
      });
      setCountdown(6);
    } finally {
      setIsSubmitting(false);
    }
  };

  const clearRoster = () => {
    if (window.confirm("Are you sure you want to clear today's local sign-in roster?")) {
      setRoster([]);
      localStorage.removeItem('oh_sign_in_roster');
    }
  };

  // Filter cities for search
  const filteredCities = citySearch.trim()
    ? ALL_CITIES.filter(c => c.toLowerCase().includes(citySearch.toLowerCase()))
    : null;

  return (
    <div className={`min-h-screen text-neutral-900 dark:text-neutral-100 transition-colors duration-300 print:bg-white print:text-black print:p-0 print:m-0 ${
      isKioskMode 
        ? 'fixed inset-0 z-[100] overflow-y-auto bg-ivory dark:bg-charcoal px-3 py-4 sm:p-6 md:p-8' 
        : 'bg-ivory dark:bg-charcoal pt-6 sm:pt-8 pb-20'
    }`}>
      
      {/* ----------------- TOP ADMIN CONTROLS TOOLBAR ----------------- */}
      <div className="max-w-3xl mx-auto px-4 mb-4 sm:mb-6 print:hidden" ref={formTopRef}>
        <div className="flex flex-wrap items-center justify-between gap-2.5 bg-white/95 dark:bg-charcoal-dark/95 backdrop-blur-md p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm text-xs">
          
          {/* Active Market & Address */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="flex items-center gap-1 font-semibold text-neutral-800 dark:text-neutral-200">
              <MapPin className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span>City:</span>
            </span>
            <button 
              type="button"
              onClick={() => setShowConfig(!showConfig)}
              className="bg-neutral-100 dark:bg-charcoal hover:bg-neutral-200 dark:hover:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 px-3 py-1 rounded-lg font-bold text-neutral-900 dark:text-neutral-100 flex items-center gap-1.5 transition-colors"
            >
              <span>{marketCity}</span>
              <Settings className="w-3 h-3 text-neutral-500" />
            </button>
            {propertyAddress && (
              <span className="text-neutral-500 dark:text-neutral-400 border-l border-neutral-300 dark:border-neutral-700 pl-2 truncate max-w-[200px]">
                {propertyAddress}
              </span>
            )}
          </div>

          {/* Action Tools */}
          <div className="flex items-center gap-2 flex-wrap">
            
            {/* Direct Open Manager Tab Button */}
            {onOpenCrm && !isKioskMode && (
              <button
                type="button"
                onClick={onOpenCrm}
                title="Open Central Manager Agent"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-bold text-[11px] transition-all shadow-sm active:scale-95"
              >
                <MessageSquareCode className="w-3.5 h-3.5" />
                <span>Manager Chat</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </button>
            )}

            {/* Quick GPS Geolocation Button */}
            <button
              type="button"
              onClick={handleDetectLocation}
              disabled={gpsLoading}
              title="Detect nearest city via GPS"
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 transition-colors font-medium text-[11px]"
            >
              <Compass className={`w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 ${gpsLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">GPS</span>
            </button>

            {/* Theme Toggle Button */}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              title={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
              className="p-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 transition-colors"
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="w-3.5 h-3.5 text-amber-400" />
              ) : (
                <Moon className="w-3.5 h-3.5 text-slate-700" />
              )}
            </button>

            {/* Print Sheet View Toggle */}
            {!isKioskMode && (
              <button
                type="button"
                onClick={() => setViewMode(viewMode === 'digital' ? 'print' : 'digital')}
                className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 transition-colors font-medium text-[11px]"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>{viewMode === 'digital' ? 'Print' : 'Digital'}</span>
              </button>
            )}

            {/* Roster Viewer */}
            <button
              type="button"
              onClick={() => setShowRoster(!showRoster)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 transition-colors font-medium text-[11px]"
            >
              <Users className="w-3.5 h-3.5" />
              <span>Roster ({roster.length})</span>
            </button>

            {/* Tablet Kiosk Mode Toggle */}
            <button
              type="button"
              onClick={toggleKioskMode}
              title={isKioskMode ? "Exit Kiosk Mode" : "Enter iPad Kiosk Mode"}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-bold uppercase tracking-wider text-[11px] transition-colors ${
                isKioskMode 
                  ? 'bg-amber-600 text-white hover:bg-amber-700' 
                  : 'bg-neutral-900 text-white hover:bg-neutral-800 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white'
              }`}
            >
              {isKioskMode ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              <span>{isKioskMode ? 'Exit Kiosk' : 'Kiosk Mode'}</span>
            </button>

          </div>
        </div>

        {/* GPS Result Toast */}
        {gpsMessage && (
          <div className={`p-2.5 mb-2 rounded-lg text-xs font-medium flex items-center justify-between ${
            gpsMessage.type === 'success' 
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300' 
              : 'bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800 text-red-800 dark:text-red-300'
          }`}>
            <span>{gpsMessage.text}</span>
            <button type="button" onClick={() => setGpsMessage(null)} className="text-xs hover:opacity-75">✕</button>
          </div>
        )}

        {/* ----------------- COLLAPSIBLE SETTINGS DRAWER ----------------- */}
        {showConfig && (
          <div className="bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 rounded-xl p-5 mb-4 shadow-xl transition-all">
            <div className="flex justify-between items-center mb-4 pb-2 border-b border-neutral-200 dark:border-neutral-800">
              <h3 className="font-serif font-bold text-sm uppercase tracking-wider text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                <Settings className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                Select City & Open House Details
              </h3>
              <button 
                type="button"
                onClick={() => setShowConfig(false)} 
                className="text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100 font-bold px-2 py-1"
              >
                Done ✕
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
              
              {/* City Selection with GPS and Grouped Counties */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[11px] uppercase tracking-wider font-bold text-neutral-700 dark:text-neutral-300">
                    Host City / CRM Market <span className="text-cyan-500">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleDetectLocation}
                    disabled={gpsLoading}
                    className="text-[11px] text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
                  >
                    <Compass className="w-3 h-3" />
                    <span>Auto-detect GPS</span>
                  </button>
                </div>

                {/* Quick Search for City */}
                <div className="relative mb-2">
                  <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search any WA city (Auburn, Kent, Seattle...)"
                    value={citySearch}
                    onChange={(e) => setCitySearch(e.target.value)}
                    autoComplete="off"
                    autoCorrect="off"
                    spellCheck={false}
                    className="w-full bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-lg pl-8 pr-3 py-2 text-neutral-900 dark:text-neutral-100 text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                  />
                  {citySearch && (
                    <button 
                      type="button"
                      onClick={() => setCitySearch('')} 
                      className="absolute right-2.5 top-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Filtered Search Results or County Grouped Dropdown */}
                {citySearch.trim() ? (
                  <div className="max-h-40 overflow-y-auto border border-neutral-200 dark:border-neutral-800 rounded-lg divide-y divide-neutral-100 dark:divide-neutral-800">
                    {filteredCities && filteredCities.length > 0 ? (
                      filteredCities.map(c => (
                        <button
                          key={c}
                          type="button"
                          onClick={() => {
                            setMarketCity(c);
                            setCitySearch('');
                          }}
                          className={`w-full text-left px-3 py-2 text-xs hover:bg-cyan-50 dark:hover:bg-charcoal flex justify-between items-center ${
                            marketCity === c ? 'bg-cyan-100/60 dark:bg-cyan-900/40 font-bold text-cyan-800 dark:text-cyan-200' : 'text-neutral-700 dark:text-neutral-300'
                          }`}
                        >
                          <span>{c}</span>
                          {marketCity === c && <Check className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />}
                        </button>
                      ))
                    ) : (
                      <div className="p-3 text-center text-neutral-500">
                        <span>No match found. </span>
                        <button 
                          type="button" 
                          onClick={() => {
                            setMarketCity(citySearch.trim());
                            setCitySearch('');
                          }}
                          className="text-cyan-600 dark:text-cyan-400 font-bold underline"
                        >
                          Use "{citySearch.trim()}"
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <select 
                    value={marketCity} 
                    onChange={(e) => setMarketCity(e.target.value)}
                    className="w-full bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-neutral-900 dark:text-neutral-100 font-medium focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                  >
                    {Object.entries(WA_COUNTIES_MARKETS).map(([county, cities]) => (
                      <optgroup key={county} label={`── ${county} ──`}>
                        {cities.map(c => (
                          <option key={c.name} value={c.name}>{c.name}</option>
                        ))}
                      </optgroup>
                    ))}
                    <optgroup label="── Other ──">
                      <option value="Custom">Custom City...</option>
                    </optgroup>
                  </select>
                )}

                {marketCity === 'Custom' && (
                  <input
                    type="text"
                    placeholder="Enter custom city..."
                    onChange={(e) => setMarketCity(e.target.value)}
                    autoComplete="off"
                    autoCorrect="off"
                    spellCheck={false}
                    className="w-full mt-2 bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                  />
                )}

                <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-1.5">
                  Over 80 cities across King, Pierce, Snohomish, & Thurston counties with instant GPS detection.
                </p>
              </div>

              {/* Property Address */}
              <div>
                <label className="block text-[11px] uppercase tracking-wider font-bold text-neutral-700 dark:text-neutral-300 mb-1.5">
                  Property Address (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 10410 SE 256th St, Kent, WA"
                  value={propertyAddress}
                  onChange={(e) => setPropertyAddress(e.target.value)}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck={false}
                  className="w-full bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                />
                <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-1.5">
                  Displays on the header banner and gets attached to CRM visitor notes.
                </p>
              </div>

            </div>
          </div>
        )}

        {/* ----------------- COLLAPSIBLE ROSTER DRAWER ----------------- */}
        {showRoster && (
          <div className="bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 rounded-xl p-5 mb-4 shadow-xl transition-all">
            <div className="flex justify-between items-center mb-4 pb-2 border-b border-neutral-200 dark:border-neutral-800">
              <h3 className="font-serif font-bold text-sm uppercase tracking-wider text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                Today's Sign-In Roster ({roster.length} visitors)
              </h3>
              <div className="flex items-center gap-3">
                {roster.length > 0 && (
                  <button 
                    type="button"
                    onClick={clearRoster}
                    className="text-[11px] uppercase tracking-wider font-bold text-red-600 hover:underline"
                  >
                    Clear Roster
                  </button>
                )}
                <button 
                  type="button"
                  onClick={() => setShowRoster(false)} 
                  className="text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100 font-bold px-2 py-1"
                >
                  Close ✕
                </button>
              </div>
            </div>

            {roster.length === 0 ? (
              <p className="text-xs text-neutral-500 py-4 text-center">No visitors signed in yet today. The roster will populate automatically as guests submit the form.</p>
            ) : (
              <div className="overflow-x-auto max-h-64 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-neutral-200 dark:border-neutral-800 text-[10px] uppercase tracking-wider text-neutral-500">
                    <tr>
                      <th className="py-2 px-2.5">Time</th>
                      <th className="py-2 px-2.5">Name</th>
                      <th className="py-2 px-2.5">Phone</th>
                      <th className="py-2 px-2.5">Email</th>
                      <th className="py-2 px-2.5">Needs</th>
                      <th className="py-2 px-2.5">Agent?</th>
                      <th className="py-2 px-2.5">Feedback</th>
                      <th className="py-2 px-2.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800 font-sans">
                    {roster.map((r, i) => (
                      <tr key={r.id || i} className="hover:bg-neutral-50 dark:hover:bg-charcoal/50">
                        <td className="py-2.5 px-2.5 font-mono text-[11px] text-neutral-500 whitespace-nowrap">{r.time}</td>
                        <td className="py-2.5 px-2.5 font-semibold text-neutral-900 dark:text-neutral-100 whitespace-nowrap">{r.name}</td>
                        <td className="py-2.5 px-2.5 text-neutral-600 dark:text-neutral-400 whitespace-nowrap">{r.phone || '—'}</td>
                        <td className="py-2.5 px-2.5 text-neutral-600 dark:text-neutral-400 whitespace-nowrap">{r.email || '—'}</td>
                        <td className="py-2.5 px-2.5 text-neutral-600 dark:text-neutral-400 text-[11px]">{Array.isArray(r.needs) ? r.needs.join(', ') : (r.needs || '—')}</td>
                        <td className="py-2.5 px-2.5 text-neutral-600 dark:text-neutral-400 whitespace-nowrap">{r.workingWithAgent || 'No'}</td>
                        <td className="py-2.5 px-2.5 text-neutral-600 dark:text-neutral-400 max-w-xs truncate" title={r.feedback}>{r.feedback || '—'}</td>
                        <td className="py-2.5 px-2.5 text-right whitespace-nowrap">
                          {r.phone ? (
                            <a
                              href={getDraftSmsUrl(r)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 bg-cyan-600 hover:bg-cyan-700 text-white rounded-md text-[11px] font-bold transition-colors shadow-sm"
                              title={`Open pre-filled text to ${r.name}`}
                            >
                              <span>💬 Text Card</span>
                            </a>
                          ) : (
                            <span className="text-neutral-400 text-[10px]">No phone</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ----------------- EXIT KIOSK CONFIRMATION MODAL ----------------- */}
      {showExitKioskModal && (
        <div className="fixed inset-0 z-[110] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-charcoal-dark border border-neutral-300 dark:border-neutral-700 rounded-2xl max-w-sm w-full p-6 text-center shadow-2xl">
            <h4 className="font-serif font-bold text-lg text-neutral-900 dark:text-white mb-2">
              Exit Kiosk Mode?
            </h4>
            <p className="text-xs text-neutral-600 dark:text-neutral-400 mb-6">
              This will reveal the website header, navigation menus, and standard browser controls.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowExitKioskModal(false)}
                className="flex-1 py-2.5 px-4 rounded-xl border border-neutral-300 dark:border-neutral-700 text-xs font-bold text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                Keep In Kiosk
              </button>
              <button
                type="button"
                onClick={confirmExitKiosk}
                className="flex-1 py-2.5 px-4 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold hover:bg-neutral-800 dark:hover:bg-neutral-100"
              >
                Exit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Container */}
      <div className="max-w-3xl mx-auto px-4">

        {/* ----------------- PRINTABLE VIEW ----------------- */}
        {viewMode === 'print' ? (
          <div className="bg-white text-black p-8 md:p-12 shadow-2xl rounded-2xl border border-neutral-200 print:shadow-none print:border-none print:p-0">
            {/* Print Header */}
            <div className="flex justify-between items-start pb-6 border-b-2 border-black/80 mb-6">
              <div className="flex items-center gap-4">
                <img 
                  src="/loki-profile.jpg" 
                  alt="Lokesh Chanana" 
                  className="w-20 h-20 rounded-full object-cover border border-black/40 scale-x-[-1]" 
                />
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-serif font-bold text-black">Lokesh Chanana</h2>
                    <span className="bg-cyan-100 text-cyan-800 text-[10px] font-bold px-2 py-0.5 rounded">Loki</span>
                  </div>
                  <p className="text-xs text-black/80 font-mono mt-0.5">hello@lokeshchanana.com</p>
                  <p className="text-xs text-black/80 font-mono">(801) 860-1052</p>
                  <p className="text-xs font-semibold text-black/90">Lakhani Team • Real Broker LLC</p>
                  {propertyAddress && (
                    <p className="text-[11px] text-black/70 mt-1 font-serif">Property: {propertyAddress} ({marketCity})</p>
                  )}
                </div>
              </div>

              <div className="text-right">
                <span className="font-serif italic text-3xl text-black/70 block" style={{ fontFamily: "'Alex Brush', 'Playfair Display', cursive" }}>
                  Welcome!
                </span>
                <h1 className="text-2xl font-serif font-bold text-black uppercase mt-1 tracking-normal">
                  Guest Registry
                </h1>
              </div>
            </div>

            {/* Print 4 repeating entry rows */}
            <div className="space-y-6">
              {[1, 2, 3, 4].map((slot) => (
                <div key={slot} className="grid grid-cols-12 gap-6 py-4 border-b border-black/20 text-xs">
                  <div className="col-span-7 space-y-3">
                    <div className="flex items-end gap-2">
                      <span className="w-16 font-medium">Name:</span>
                      <div className="flex-1 border-b border-black/60 h-4"></div>
                    </div>
                    <div className="flex items-end gap-2">
                      <span className="w-16 font-medium">Phone #:</span>
                      <div className="flex-1 border-b border-black/60 h-4"></div>
                    </div>
                    <div className="flex items-end gap-2">
                      <span className="w-16 font-medium">Email:</span>
                      <div className="flex-1 border-b border-black/60 h-4"></div>
                    </div>
                    <div className="flex items-end gap-2">
                      <span className="w-16 font-medium">Feedback:</span>
                      <div className="flex-1 border-b border-black/60 h-4"></div>
                    </div>
                    <div className="flex items-center gap-4 pt-1">
                      <span className="font-medium">Are you working with an agent?</span>
                      <span className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 border border-black inline-block"></span> Yes</span>
                      <span className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 border border-black inline-block"></span> No</span>
                    </div>
                  </div>

                  <div className="col-span-5 pl-4 border-l border-black/20">
                    <p className="font-serif font-bold tracking-widest uppercase text-[11px] mb-2.5">C U R R E N T &nbsp; N E E D S ?</p>
                    <div className="space-y-2 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="w-3.5 h-3.5 border border-black inline-block"></span>
                        <span>Looking to buy now</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3.5 h-3.5 border border-black inline-block"></span>
                        <span>Just browsing</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3.5 h-3.5 border border-black inline-block"></span>
                        <span>Plan to buy within a year</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3.5 h-3.5 border border-black inline-block"></span>
                        <span>Interested in selling</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Print Footer */}
            <div className="flex justify-between items-center pt-6 mt-6 border-t-2 border-black/80 text-[10px] tracking-widest font-mono uppercase">
              <span>REAL BROKER LLC</span>
              <span>LICENSE #26006634</span>
            </div>

            {/* Print button when on screen */}
            <div className="mt-8 text-center print:hidden">
              <button 
                type="button"
                onClick={() => window.print()} 
                className="bg-black text-white px-8 py-3 text-xs font-bold uppercase tracking-widest hover:bg-neutral-800 transition-colors inline-flex items-center gap-2 rounded-xl"
              >
                <Printer className="w-4 h-4" />
                Print This Sheet
              </button>
            </div>
          </div>
        ) : (

        /* ----------------- DIGITAL SIGN-IN CARD ----------------- */
        <div className="bg-white dark:bg-charcoal-dark rounded-2xl md:rounded-3xl border border-neutral-200/90 dark:border-neutral-800 shadow-xl dark:shadow-2xl overflow-hidden transition-colors duration-300">
          
          {/* Header Banner */}
          <div className="p-6 sm:p-8 md:p-10 border-b border-neutral-200 dark:border-neutral-800 bg-gradient-to-br from-neutral-50 via-white to-neutral-50 dark:from-charcoal/60 dark:via-charcoal-dark dark:to-charcoal/40">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-5">
              
              {/* Agent Branding */}
              <div className="flex items-center gap-4">
                <div className="relative flex-shrink-0">
                  <img 
                    src="/loki-profile.jpg" 
                    alt="Lokesh Chanana" 
                    className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover object-[50%_25%] border-2 border-neutral-300 dark:border-neutral-700 shadow-md scale-x-[-1]" 
                  />
                  <div className="absolute -bottom-1 -right-1 bg-emerald-500 w-4 h-4 rounded-full border-2 border-white dark:border-charcoal-dark" title="Open House Host Active"></div>
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg sm:text-2xl font-serif font-bold text-neutral-900 dark:text-white">
                      Lokesh Chanana
                    </h2>
                    <span className="bg-cyan-100 dark:bg-cyan-950/70 text-cyan-800 dark:text-cyan-300 font-bold px-2 py-0.5 rounded text-[11px] border border-cyan-300 dark:border-cyan-800">
                      Loki
                    </span>
                  </div>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 font-medium mt-0.5">
                    Lakhani Team • Real Broker LLC
                  </p>
                  <div className="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                    <a href="tel:8018601052" className="hover:text-cyan-600 dark:hover:text-cyan-400 font-mono flex items-center gap-1">
                      <Phone className="w-3 h-3" /> (801) 860-1052
                    </a>
                  </div>
                </div>
              </div>

              {/* Title & Property Badge */}
              <div className="text-left sm:text-right w-full sm:w-auto pt-2 sm:pt-0 border-t sm:border-t-0 border-neutral-200 dark:border-neutral-800">
                <span 
                  className="font-serif italic text-2xl sm:text-3xl text-neutral-500 dark:text-neutral-400 block leading-tight" 
                  style={{ fontFamily: "'Alex Brush', 'Playfair Display', cursive, serif" }}
                >
                  Welcome!
                </span>
                <h1 className="text-2xl sm:text-3xl font-serif font-bold text-neutral-900 dark:text-white uppercase tracking-tight">
                  Guest Check-In
                </h1>
                <div className="inline-flex items-center gap-1.5 mt-1.5 bg-neutral-100 dark:bg-charcoal px-2.5 py-1 rounded-md text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
                  <MapPin className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                  <span>{propertyAddress ? `${propertyAddress} (${marketCity})` : `${marketCity} Open House`}</span>
                </div>
              </div>

            </div>
          </div>

          {/* Form Content Area */}
          <div className="p-6 sm:p-8 md:p-10">

            {/* SUCCESS CONFIRMATION VIEW */}
            {submittedData ? (
              <div className="py-10 px-4 text-center max-w-lg mx-auto animate-fadeIn">
                <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-950/60 border-2 border-emerald-500 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl shadow-emerald-500/10">
                  <CheckCircle2 className="w-10 h-10" />
                </div>

                <span className="text-xs uppercase tracking-widest text-emerald-600 dark:text-emerald-400 font-bold block mb-2">
                  {submittedData.isReturning ? 'Returning Visitor' : 'Sign-In Verified'}
                </span>

                <h3 className="text-2xl sm:text-3xl font-serif font-bold text-neutral-900 dark:text-white mb-3">
                  {submittedData.message || (submittedData.isReturning ? `Welcome back, ${submittedData.name}!` : `Welcome, ${submittedData.name}!`)}
                </h3>

                <p className="text-sm font-sans text-neutral-600 dark:text-neutral-300 mb-6 leading-relaxed">
                  {submittedData.isReturning ? (
                    <>
                      Great to see you again! Thank you for stopping by today's open house in <strong className="text-neutral-900 dark:text-white">{submittedData.market}</strong>. Enjoy touring the home!
                    </>
                  ) : (
                    <>
                      Thank you for visiting today's open house in <strong className="text-neutral-900 dark:text-white">{submittedData.market}</strong>. 
                      Enjoy touring the home! Please feel free to ask Loki any questions about the floorplan, finishes, HOA, or neighborhood comps.
                    </>
                  )}
                </p>

                {/* Reset Next Visitor Button */}
                <div className="space-y-4 pt-2">
                  <button
                    type="button"
                    onClick={resetForm}
                    className="w-full bg-neutral-900 hover:bg-neutral-800 dark:bg-white dark:hover:bg-neutral-100 text-white dark:text-neutral-900 py-4 px-6 rounded-xl text-sm font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Sign In Next Visitor</span>
                  </button>

                  <p className="text-xs text-neutral-500 dark:text-neutral-400 font-mono">
                    Screen will automatically refresh for next guest in {countdown}s...
                  </p>
                </div>
              </div>
            ) : (

              /* SIGN IN FORM (iPad & Touch Optimized) */
              <form 
                onSubmit={handleSubmit} 
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                className="space-y-6 sm:space-y-8"
              >
                
                {submitError && (
                  <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800 text-red-700 dark:text-red-300 rounded-xl text-xs font-semibold">
                    {submitError}
                  </div>
                )}

                {/* Section 1: Contact Information */}
                <div className="space-y-4 sm:space-y-5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
                    <span>1. Guest Contact Information</span>
                  </h3>

                  {/* Full Name */}
                  <div>
                    <label 
                      htmlFor="guest-name"
                      className="block text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-1.5"
                    >
                      Full Name <span className="text-cyan-600 dark:text-cyan-400">*</span>
                    </label>
                    <input
                      id="guest-name"
                      name="oh_visitor_name"
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Sarah Jenkins"
                      autoComplete="off"
                      autoCorrect="off"
                      spellCheck={false}
                      autoCapitalize="words"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      enterKeyHint="next"
                      className="w-full bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3.5 text-base text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:bg-white dark:focus:bg-charcoal-dark focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 focus:outline-none transition-all shadow-sm"
                    />
                  </div>

                  {/* Phone & Email side-by-side with large touch inputs */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5">
                    <div>
                      <label 
                        htmlFor="guest-phone"
                        className="block text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-1.5"
                      >
                        Phone Number <span className="text-cyan-600 dark:text-cyan-400">*</span>
                      </label>
                      <div className="relative">
                        <Phone className="w-4 h-4 text-neutral-400 absolute left-3.5 top-4" />
                        <input
                          id="guest-phone"
                          name="oh_visitor_phone"
                          type="tel"
                          inputMode="tel"
                          value={phone}
                          onChange={handlePhoneChange}
                          placeholder="(206) 555-0199"
                          autoComplete="off"
                          autoCorrect="off"
                          spellCheck={false}
                          data-lpignore="true"
                          data-1p-ignore="true"
                          enterKeyHint="next"
                          className={`w-full bg-neutral-50 dark:bg-charcoal border ${
                            submitError && !phone.replace(/\D/g, '').length && !email.trim()
                              ? 'border-red-400 dark:border-red-500'
                              : 'border-neutral-300 dark:border-neutral-700'
                          } rounded-xl pl-10 pr-4 py-3.5 text-base text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:bg-white dark:focus:bg-charcoal-dark focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 focus:outline-none transition-all shadow-sm`}
                        />
                      </div>
                    </div>

                    <div>
                      <label 
                        htmlFor="guest-email"
                        className="block text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-1.5"
                      >
                        Email Address <span className="text-cyan-600 dark:text-cyan-400">*</span>
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 text-neutral-400 absolute left-3.5 top-4" />
                        <input
                          id="guest-email"
                          name="oh_visitor_email"
                          type="email"
                          value={email}
                          onChange={(e) => {
                            if (submitError) setSubmitError(null);
                            setEmail(e.target.value);
                          }}
                          placeholder="sarah@example.com"
                          autoComplete="off"
                          autoCorrect="off"
                          spellCheck={false}
                          autoCapitalize="none"
                          data-lpignore="true"
                          data-1p-ignore="true"
                          inputMode="email"
                          enterKeyHint="next"
                          className={`w-full bg-neutral-50 dark:bg-charcoal border ${
                            submitError && !phone.replace(/\D/g, '').length && !email.trim()
                              ? 'border-red-400 dark:border-red-500'
                              : 'border-neutral-300 dark:border-neutral-700'
                          } rounded-xl pl-10 pr-4 py-3.5 text-base text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:bg-white dark:focus:bg-charcoal-dark focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 focus:outline-none transition-all shadow-sm`}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section 2: Working with an Agent */}
                <div className="pt-2 space-y-3">
                  <label className="block text-sm font-semibold text-neutral-800 dark:text-neutral-200">
                    Are you currently working with a real estate agent?
                  </label>
                  
                  <div className="grid grid-cols-2 gap-3 sm:gap-4">
                    <button
                      type="button"
                      onClick={() => setWorkingWithAgent('No')}
                      className={`py-3.5 px-4 rounded-xl text-sm font-bold transition-all border flex items-center justify-center gap-2 ${
                        workingWithAgent === 'No'
                          ? 'bg-neutral-900 text-white border-neutral-900 dark:bg-white dark:text-neutral-900 dark:border-white shadow-md'
                          : 'bg-neutral-50 dark:bg-charcoal text-neutral-700 dark:text-neutral-300 border-neutral-300 dark:border-neutral-700 hover:border-neutral-400'
                      }`}
                    >
                      <span>No, touring independently</span>
                      {workingWithAgent === 'No' && <Check className="w-4 h-4" />}
                    </button>

                    <button
                      type="button"
                      onClick={() => setWorkingWithAgent('Yes')}
                      className={`py-3.5 px-4 rounded-xl text-sm font-bold transition-all border flex items-center justify-center gap-2 ${
                        workingWithAgent === 'Yes'
                          ? 'bg-neutral-900 text-white border-neutral-900 dark:bg-white dark:text-neutral-900 dark:border-white shadow-md'
                          : 'bg-neutral-50 dark:bg-charcoal text-neutral-700 dark:text-neutral-300 border-neutral-300 dark:border-neutral-700 hover:border-neutral-400'
                      }`}
                    >
                      <span>Yes, I have an agent</span>
                      {workingWithAgent === 'Yes' && <Check className="w-4 h-4" />}
                    </button>
                  </div>

                  {workingWithAgent === 'Yes' && (
                    <div className="mt-3 animate-fadeIn">
                      <label 
                        htmlFor="agent-name-input"
                        className="block text-xs font-semibold text-neutral-600 dark:text-neutral-400 mb-1"
                      >
                        Agent's Name & Brokerage (Optional)
                      </label>
                      <input
                        id="agent-name-input"
                        name="oh_agent_name"
                        type="text"
                        value={agentName}
                        onChange={(e) => setAgentName(e.target.value)}
                        placeholder="e.g. John Doe, Windermere"
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck={false}
                        data-lpignore="true"
                        data-1p-ignore="true"
                        enterKeyHint="next"
                        className="w-full bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 text-base text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:bg-white dark:focus:bg-charcoal-dark focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                      />
                    </div>
                  )}
                </div>

                {/* Section 3: Current Needs / Plans */}
                <div className="pt-2 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
                      What are your current plans?
                    </label>
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">Select all that apply</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {NEED_OPTIONS.map((option) => {
                      const isChecked = selectedNeeds.includes(option.label);
                      return (
                        <div
                          key={option.id}
                          onClick={() => toggleNeed(option.label)}
                          role="checkbox"
                          aria-checked={isChecked}
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === ' ' || e.key === 'Enter') {
                              e.preventDefault();
                              toggleNeed(option.label);
                            }
                          }}
                          className={`cursor-pointer p-4 rounded-xl border transition-all flex items-start gap-3 select-none ${
                            isChecked
                              ? 'bg-cyan-50/80 dark:bg-cyan-950/40 border-cyan-500 dark:border-cyan-400 shadow-sm'
                              : 'bg-neutral-50 dark:bg-charcoal border-neutral-300 dark:border-neutral-700 hover:border-neutral-400 dark:hover:border-neutral-600'
                          }`}
                        >
                          <span className="text-xl flex-shrink-0 mt-0.5">{option.icon}</span>
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-bold ${
                              isChecked 
                                ? 'text-cyan-900 dark:text-cyan-200' 
                                : 'text-neutral-800 dark:text-neutral-200'
                            }`}>
                              {option.label}
                            </p>
                            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 leading-tight">
                              {option.desc}
                            </p>
                          </div>
                          <div className={`w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                            isChecked 
                              ? 'bg-cyan-600 border-cyan-600 text-white' 
                              : 'border-neutral-400 dark:border-neutral-600 bg-white dark:bg-charcoal-dark'
                          }`}>
                            {isChecked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Section 4: Feedback / Thoughts (Optional) */}
                <div className="pt-2 space-y-1.5">
                  <label 
                    htmlFor="guest-feedback"
                    className="block text-sm font-semibold text-neutral-800 dark:text-neutral-200"
                  >
                    Feedback / Thoughts on this Home <span className="text-xs text-neutral-500 font-normal">(Optional)</span>
                  </label>
                  <textarea
                    id="guest-feedback"
                    name="oh_feedback"
                    rows={2}
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="What do you think of the layout, yard, kitchen, or price?"
                    autoComplete="off"
                    autoCorrect="off"
                    spellCheck={false}
                    enterKeyHint="done"
                    className="w-full bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 text-base text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:bg-white dark:focus:bg-charcoal-dark focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all resize-none shadow-sm"
                  ></textarea>
                </div>

                {/* TCPA / SMS Consent Notice */}
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 text-center leading-relaxed px-2">
                  By clicking Submit, you consent to receive a text message from Lokesh Chanana (Loki) with property details and follow-up. Consent is not a condition of purchase. Message and data rates may apply.
                </p>

                {/* Submit Action Button */}
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full flex items-center justify-center gap-3 bg-neutral-900 hover:bg-neutral-800 dark:bg-white dark:hover:bg-neutral-100 text-white dark:text-neutral-900 py-4 px-6 rounded-xl text-base font-bold uppercase tracking-wider transition-all disabled:opacity-50 shadow-xl shadow-neutral-900/10 active:scale-[0.99]"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                        <span>Submitting...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5 text-cyan-400 dark:text-cyan-600" />
                        <span>Submit</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Discreet Privacy Note & iPad Tips */}
                <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-neutral-500 dark:text-neutral-400">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                    <span>Discrete & Secure Registry • Never sold or distributed</span>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-neutral-400">
                    <Info className="w-3 h-3" />
                    <span>iPad Tip: Spread two fingers on floating keyboard to dock it full-width</span>
                  </div>
                </div>

              </form>
            )}

          </div>

          {/* Footer Panel */}
          <div className="p-4 sm:p-6 bg-neutral-50 dark:bg-charcoal/40 border-t border-neutral-200 dark:border-neutral-800 flex flex-col sm:flex-row justify-between items-center gap-3 text-[11px] font-mono uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-neutral-700 dark:text-neutral-300">REAL BROKER LLC</span>
              <span>•</span>
              <span>LICENSE #26006634</span>
            </div>

            <div className="flex items-center gap-4">
              <img src="/real-logo.png" alt="REAL" className="h-4 object-contain dark:invert opacity-70" />
              <img src="/lakhani-logo.png" alt="Lakhani Team" className="h-5 object-contain invert dark:invert-0 opacity-70" />
              <span className="text-[10px]">Equal Housing Opportunity</span>
            </div>
          </div>

        </div>
        )}

      </div>

      {/* Floating Action Button to quickly jump to Manager Chat */}
      {!isKioskMode && onOpenCrm && (
        <div className="fixed bottom-6 right-6 z-40 print:hidden">
          <button
            type="button"
            onClick={onOpenCrm}
            className="flex items-center gap-2.5 px-4 py-3 rounded-full bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-white font-bold text-xs shadow-2xl border border-neutral-700/20 hover:scale-105 active:scale-95 transition-all group"
            title="Open Central Manager Agent"
          >
            <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white shadow-sm">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <span>Manager Chat</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </button>
        </div>
      )}

    </div>
  );
}
