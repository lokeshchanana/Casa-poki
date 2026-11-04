import React, { useState, useEffect, useMemo } from 'react';
import AvatarCharacter from './AvatarCharacter';
import {
  Coffee,
  Server,
  Activity,
  Users,
  MessageSquare,
  Sparkles,
  Info,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  Compass,
  Building,
  CheckCircle2,
  Flame,
  ArrowRight
} from 'lucide-react';

export default function OfficeFloorMap({
  agents = [],
  recentFlows = [],
  containers = [],
  monitors = [],
  onSelectAgent,
  onOpenChat,
}) {
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [activeAgentId, setActiveAgentId] = useState(null);
  const [steamActive, setSteamActive] = useState(false);
  const [waterBubbles, setWaterBubbles] = useState(false);
  const [serverBlinkMode, setServerBlinkMode] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1); // 0.85, 1, 1.15

  // Map agent ID to live state from parent
  const agentStateMap = useMemo(() => {
    const map = {};
    agents.forEach((a) => {
      map[a.id] = a;
    });
    return map;
  }, [agents]);

  // Determine current simulated locations for idle vs busy agents
  // (Deterministic cycle based on current minute + agent ID)
  const [currentMinute, setCurrentMinute] = useState(new Date().getMinutes());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentMinute(new Date().getMinutes());
    }, 15000); // Check location shift every 15s
    return () => clearInterval(timer);
  }, []);

  // Compute live positioning on the floor map
  const agentLocations = useMemo(() => {
    const locs = {};
    const agentIds = ['manager', 'it', 'auditor', 'intake', 'finance', 'marketing', 'cma'];

    agentIds.forEach((id, index) => {
      const liveAgent = agentStateMap[id] || {};
      const isLiveActive = liveAgent.status === 'active';

      if (isLiveActive) {
        // ALWAYS at home desk when working
        locs[id] = {
          zone: `desk_${id}`,
          state: 'active',
          locationLabel: `At Personal Workstation (Active Task)`,
          activity: `Focused processing on live request`,
        };
        return;
      }

      // Idle Rotation Cycle: Desk (50%), Kitchen (20%), Lounge (15%), Watercooler (10%), Boardroom (5%)
      const seed = (currentMinute + index * 7) % 100;

      if (seed < 45) {
        locs[id] = {
          zone: `desk_${id}`,
          state: 'idle',
          locationLabel: `At Workstation Desk`,
          activity: liveAgent.default_activity || 'Reviewing documentation at desk',
        };
      } else if (seed < 65) {
        locs[id] = {
          zone: 'kitchen_cafe',
          state: 'coffee',
          locationLabel: `Kitchen Café & Espresso Bar`,
          activity: 'Brewing a fresh double espresso at the counter ☕',
        };
      } else if (seed < 80) {
        locs[id] = {
          zone: 'lounge_sofa',
          state: 'relaxing',
          locationLabel: `Leisure Lounge Sofa`,
          activity: 'Reading Bellevue luxury real estate journal on the couch 🛋️',
        };
      } else if (seed < 92) {
        locs[id] = {
          zone: 'watercooler',
          state: 'chatting',
          locationLabel: `Watercooler Hallway Nook`,
          activity: 'Chatting with colleagues about Northwest market trends 🗣️',
        };
      } else {
        locs[id] = {
          zone: 'boardroom',
          state: 'idle',
          locationLabel: `Olympic Boardroom (Conference Table)`,
          activity: 'Reviewing strategic goals and roadmap on the glass whiteboard 📋',
        };
      }
    });

    return locs;
  }, [agentStateMap, currentMinute]);

  const handleAgentClick = (agentId) => {
    setActiveAgentId(agentId);
    const ag = agentStateMap[agentId];
    if (onSelectAgent && ag) {
      onSelectAgent(ag);
    }
  };

  const triggerEspresso = () => {
    setSteamActive(true);
    setTimeout(() => setSteamActive(false), 6000);
  };

  const triggerWatercooler = () => {
    setWaterBubbles(true);
    setTimeout(() => setWaterBubbles(false), 5000);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Map Control Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-serif font-bold text-neutral-800 dark:text-neutral-200">
            <Compass className="w-4 h-4 text-indigo-500" />
            <span>Bellevue HQ Floor 4 Blueprint</span>
          </div>
          <span className="hidden sm:inline text-neutral-400">•</span>
          <span className="hidden sm:inline text-neutral-500 text-[11px]">
            Interactive Architectural Plan with Real-Time Agent Simulation
          </span>
        </div>

        {/* Zoom & Quick Actions */}
        <div className="flex items-center gap-2">
          <div className="flex items-center p-0.5 rounded-lg bg-neutral-100 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.85, z - 0.1))}
              className="p-1 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 text-[10px] font-mono font-bold text-neutral-700 dark:text-neutral-300">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(1.25, z + 0.1))}
              className="p-1 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            type="button"
            onClick={triggerEspresso}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border flex items-center gap-1.5 transition-all ${
              steamActive
                ? 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-700 animate-pulse'
                : 'bg-neutral-50 dark:bg-charcoal border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-amber-400'
            }`}
            title="Brew espresso in kitchen café"
          >
            <Coffee className="w-3.5 h-3.5 text-amber-500" />
            <span>{steamActive ? 'Brewing...' : 'Brew Coffee'}</span>
          </button>
        </div>
      </div>

      {/* Main Architectural Floor Canvas */}
      <div className="relative rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden p-4 sm:p-6 transition-all">
        {/* Floor Pattern Background (Oak herringbone styling) */}
        <div
          className="overflow-x-auto pb-4 transition-transform origin-top-left"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <div className="min-w-[1020px] max-w-[1200px] mx-auto relative rounded-xl border-4 border-neutral-800/80 dark:border-neutral-700/80 bg-[#FAF9F5] dark:bg-[#16171A] p-4 shadow-inner">
            
            {/* Compass Rose Header */}
            <div className="absolute top-2 right-4 flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-neutral-400 dark:text-neutral-600 pointer-events-none">
              <span>N</span>
              <div className="w-2 h-2 border-t-2 border-r-2 border-indigo-400 rotate-45" />
              <span>Bellevue, WA</span>
            </div>

            {/* TOP ROW: EXECUTIVE SUITE + TECH LAB + FINANCE + MARKETING */}
            <div className="grid grid-cols-12 gap-3 mb-3">
              
              {/* ROOM 101: Corner Executive Suite (Marcus Vance) */}
              <div
                onClick={() => setSelectedRoom('Room 101: Executive Suite')}
                className="col-span-3 h-64 rounded-xl border-2 border-amber-800/40 dark:border-amber-600/30 bg-[#F4EFE6]/70 dark:bg-[#1F1D1A]/70 p-3 relative flex flex-col justify-between group hover:border-indigo-400 transition-colors shadow-xs"
              >
                {/* Room Label */}
                <div className="flex items-center justify-between border-b border-amber-900/10 dark:border-amber-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-900 dark:text-amber-400">
                    Suite 101 • Executive
                  </span>
                  <span className="text-[9px] text-neutral-400">Glass Wall</span>
                </div>

                {/* Skyline Glass Window on North Edge */}
                <div className="absolute top-0 left-10 right-10 h-1.5 bg-sky-200 dark:bg-sky-900/80 rounded-b shadow-xs flex items-center justify-center">
                  <span className="text-[7px] text-sky-700 dark:text-sky-300 uppercase">Skyline View</span>
                </div>

                {/* Desk Furniture & Character */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  {/* Large Walnut Executive Desk */}
                  <div className="w-36 h-20 rounded-lg bg-[#5C4033] dark:bg-[#3D2817] border-2 border-[#3D2817] dark:border-[#24170D] shadow-md relative flex flex-col items-center justify-center p-2">
                    {/* Desk Accessories */}
                    <div className="absolute top-1 left-2 flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-amber-200 border border-amber-600" title="Coffee mug" />
                      <div className="w-3 h-1 bg-neutral-200 rounded-xs" title="Business Card" />
                    </div>
                    {/* Executive Laptop */}
                    <div className="w-10 h-7 rounded bg-neutral-800 border border-neutral-600 flex items-center justify-center shadow-xs">
                      <div className="w-7 h-4 bg-indigo-500/80 rounded-xs animate-pulse" />
                    </div>
                    <div className="w-12 h-1 bg-neutral-400 rounded-full mt-1" />
                  </div>

                  {/* Marcus Avatar Placement at Desk if at home */}
                  {agentLocations.manager?.zone === 'desk_manager' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentClick('manager');
                      }}
                      className="absolute -top-4 cursor-pointer hover:scale-110 transition-transform"
                    >
                      <AvatarCharacter
                        agentId="manager"
                        state={agentLocations.manager.state}
                        size={56}
                      />
                    </div>
                  )}

                  {/* Leather Guest Chairs */}
                  <div className="flex justify-between w-32 mt-2">
                    <div className="w-8 h-8 rounded-full bg-[#3E2723] border border-amber-950 shadow-xs" title="Guest Chair 1" />
                    <div className="w-8 h-8 rounded-full bg-[#3E2723] border border-amber-950 shadow-xs" title="Guest Chair 2" />
                  </div>
                </div>

                {/* Potted Fiddle Leaf Fig Tree */}
                <div className="absolute bottom-2 left-2 flex items-center gap-1 text-[9px] text-emerald-700 dark:text-emerald-400">
                  <div className="w-4 h-4 rounded-full bg-emerald-600 border border-emerald-800 shadow-xs flex items-center justify-center text-[8px] text-white">
                    🌿
                  </div>
                </div>

                {/* Plaque / License */}
                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Marcus Vance • Managing Principal
                </div>
              </div>

              {/* ROOM 102: Tech & Systems Lab / DevOps Pod (Ian Torres) */}
              <div
                onClick={() => setSelectedRoom('Room 102: Tech & DevOps Lab')}
                className="col-span-3 h-64 rounded-xl border-2 border-emerald-800/40 dark:border-emerald-600/30 bg-[#EBF7F2]/70 dark:bg-[#14241E]/70 p-3 relative flex flex-col justify-between group hover:border-emerald-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-emerald-900/10 dark:border-emerald-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-400 flex items-center gap-1">
                    <Server className="w-3 h-3 text-emerald-500" />
                    Room 102 • DevOps Lab
                  </span>
                  <span className="text-[9px] text-emerald-600 dark:text-emerald-400 font-mono font-bold">
                    {containers.filter((c) => c.state === 'running').length}/17 Up
                  </span>
                </div>

                <div className="flex-1 flex items-center justify-between relative mt-2 px-1">
                  {/* Left: Server Rack with Pulsing LED activity lights */}
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      setServerBlinkMode(!serverBlinkMode);
                    }}
                    className="w-14 h-40 rounded-lg bg-neutral-900 border-2 border-neutral-700 shadow-lg p-1.5 flex flex-col justify-between cursor-pointer hover:border-emerald-400 transition-colors"
                    title="Casa-Poki Server Rack (17 Containers) - Click to toggle LED pattern"
                  >
                    <div className="text-[7px] font-mono text-neutral-400 uppercase tracking-tighter text-center border-b border-neutral-800 pb-0.5">
                      RACK-01
                    </div>
                    {/* Pulsing Server Units */}
                    {[1, 2, 3, 4, 5, 6].map((unit) => (
                      <div key={unit} className="flex items-center justify-between py-0.5 px-1 bg-neutral-800 rounded-xs">
                        <span className="w-1.5 h-1 bg-neutral-600 rounded-xs" />
                        <div className="flex items-center gap-1">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              unit === 2
                                ? 'bg-amber-400'
                                : 'bg-emerald-400'
                            } ${serverBlinkMode ? 'animate-pulse' : ''}`}
                          />
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                        </div>
                      </div>
                    ))}
                    <div className="text-[6px] text-emerald-400 font-mono text-center">99.98% OK</div>
                  </div>

                  {/* Right: Ian's Workstation Desk */}
                  <div className="flex-1 flex flex-col items-center justify-center relative ml-3">
                    <div className="w-32 h-18 rounded-lg bg-neutral-800 border-2 border-neutral-700 shadow-md flex flex-col items-center justify-center p-1.5 relative">
                      {/* Dual Ultrawide Displays */}
                      <div className="flex items-center gap-1">
                        <div className="w-12 h-6 rounded-xs bg-black border border-emerald-600/60 p-0.5">
                          <div className="w-full h-full bg-emerald-950/80 text-[6px] font-mono text-emerald-400 flex items-center justify-center">
                            kuma:up
                          </div>
                        </div>
                        <div className="w-12 h-6 rounded-xs bg-black border border-cyan-600/60 p-0.5">
                          <div className="w-full h-full bg-cyan-950/80 text-[6px] font-mono text-cyan-400 flex items-center justify-center">
                            docker:17
                          </div>
                        </div>
                      </div>
                      {/* Mechanical Keyboard */}
                      <div className="w-14 h-2 bg-neutral-700 rounded-xs mt-1 border border-neutral-600" />
                    </div>

                    {/* Ian Avatar at Workstation */}
                    {agentLocations.it?.zone === 'desk_it' && (
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAgentClick('it');
                        }}
                        className="absolute -top-6 cursor-pointer hover:scale-110 transition-transform"
                      >
                        <AvatarCharacter
                          agentId="it"
                          state={agentLocations.it.state}
                          size={54}
                        />
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-mono">
                  Ian Torres • IT Infrastructure Guardian
                </div>
              </div>

              {/* ROOM 104: Financial Controller Office (Fiona Banks) */}
              <div
                onClick={() => setSelectedRoom('Room 104: Financial Controller')}
                className="col-span-3 h-64 rounded-xl border-2 border-teal-800/40 dark:border-teal-600/30 bg-[#EDF8F7]/70 dark:bg-[#142322]/70 p-3 relative flex flex-col justify-between group hover:border-teal-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-teal-900/10 dark:border-teal-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-teal-900 dark:text-teal-400">
                    Room 104 • Finance
                  </span>
                  <span className="text-[9px] text-teal-600 dark:text-teal-400 font-mono">Actual Budget</span>
                </div>

                {/* Desk & Ledgers */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  {/* Financial Desk with Banker's Green Lamp */}
                  <div className="w-34 h-20 rounded-lg bg-[#2E4A47] border-2 border-[#1B3230] shadow-md relative flex flex-col items-center justify-center p-2">
                    {/* Banker's Green Lamp on Left */}
                    <div className="absolute top-1 left-2 flex items-center gap-1">
                      <div className="w-3 h-2 rounded-t-sm bg-emerald-500 border border-emerald-300 shadow-xs" title="Banker's Lamp" />
                      <div className="w-2 h-2 rounded-xs bg-amber-100" title="Calculator" />
                    </div>
                    {/* Spreadsheets Screen */}
                    <div className="w-12 h-7 rounded bg-neutral-900 border border-teal-500 p-0.5">
                      <div className="w-full h-full bg-teal-950 text-[6px] font-mono text-teal-300 flex items-center justify-center">
                        GL: $ OK
                      </div>
                    </div>
                    {/* Ledger Binders on Right */}
                    <div className="absolute bottom-1 right-2 flex gap-0.5">
                      <div className="w-1 h-3 bg-red-700 rounded-xs" />
                      <div className="w-1 h-3 bg-blue-700 rounded-xs" />
                      <div className="w-1 h-3 bg-emerald-700 rounded-xs" />
                    </div>
                  </div>

                  {/* Fiona Avatar at Desk */}
                  {agentLocations.finance?.zone === 'desk_finance' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentClick('finance');
                      }}
                      className="absolute -top-5 cursor-pointer hover:scale-110 transition-transform"
                    >
                      <AvatarCharacter
                        agentId="finance"
                        state={agentLocations.finance.state}
                        size={54}
                      />
                    </div>
                  )}
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Fiona Banks • Financial Controller
                </div>
              </div>

              {/* ROOM 105: Marketing & Creative Studio (Maya Reyes) */}
              <div
                onClick={() => setSelectedRoom('Room 105: Marketing Creative Studio')}
                className="col-span-3 h-64 rounded-xl border-2 border-rose-800/40 dark:border-rose-600/30 bg-[#FDF2F4]/70 dark:bg-[#251619]/70 p-3 relative flex flex-col justify-between group hover:border-rose-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-rose-900/10 dark:border-rose-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-rose-900 dark:text-rose-400">
                    Room 105 • Studio
                  </span>
                  <span className="text-[9px] text-rose-500 font-mono">Creative</span>
                </div>

                {/* Drafting Table & Moodboard */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  {/* Angled Drafting Desk */}
                  <div className="w-34 h-20 rounded-lg bg-[#E2D8C6] dark:bg-[#382B29] border-2 border-[#C9BCA8] dark:border-[#523F3C] shadow-md relative flex flex-col items-center justify-center p-2">
                    {/* Color Swatches */}
                    <div className="absolute top-1 left-2 flex gap-0.5">
                      <span className="w-1.5 h-2 bg-rose-500 rounded-xs" />
                      <span className="w-1.5 h-2 bg-amber-500 rounded-xs" />
                      <span className="w-1.5 h-2 bg-indigo-500 rounded-xs" />
                    </div>
                    {/* Graphics Tablet with Stylus */}
                    <div className="w-11 h-8 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center">
                      <span className="text-[8px] text-rose-300 font-bold">🎨 Art</span>
                    </div>
                  </div>

                  {/* Maya Avatar at Desk */}
                  {agentLocations.marketing?.zone === 'desk_marketing' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentClick('marketing');
                      }}
                      className="absolute -top-5 cursor-pointer hover:scale-110 transition-transform"
                    >
                      <AvatarCharacter
                        agentId="marketing"
                        state={agentLocations.marketing.state}
                        size={54}
                      />
                    </div>
                  )}
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Maya Reyes • Creative Director
                </div>
              </div>

            </div>

            {/* MIDDLE ROW: QA & AUDIT + OLYMPIC BOARDROOM + BREAKOUT PODS + CMA LAB */}
            <div className="grid grid-cols-12 gap-3 mb-3">
              
              {/* ROOM 103: Compliance & QA Pod (Audrey Chen) */}
              <div
                onClick={() => setSelectedRoom('Room 103: Compliance & QA Pod')}
                className="col-span-3 h-64 rounded-xl border-2 border-amber-700/40 dark:border-amber-500/30 bg-[#FFFBEB]/70 dark:bg-[#231E12]/70 p-3 relative flex flex-col justify-between group hover:border-amber-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-amber-900/10 dark:border-amber-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-900 dark:text-amber-400">
                    Room 103 • QA & Audit
                  </span>
                  <span className="text-[9px] text-amber-600 dark:text-amber-400 font-mono font-bold">
                    Zero Stray Rule
                  </span>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  {/* Audit Workstation */}
                  <div className="w-34 h-20 rounded-lg bg-neutral-200 dark:bg-neutral-800 border-2 border-neutral-300 dark:border-neutral-700 shadow-md relative flex flex-col items-center justify-center p-2">
                    {/* Stamp Pad & Clipboard */}
                    <div className="absolute top-1 left-2 flex items-center gap-1">
                      <div className="w-2.5 h-2.5 rounded-xs bg-rose-600 text-[6px] text-white flex items-center justify-center" title="Approved Stamp">
                        ✓
                      </div>
                      <div className="w-2.5 h-3.5 bg-amber-200 rounded-xs border border-amber-400" title="Audit Checklist" />
                    </div>
                    {/* QA Screen */}
                    <div className="w-12 h-7 rounded bg-neutral-900 border border-amber-500 p-0.5">
                      <div className="w-full h-full bg-neutral-950 text-[6px] font-mono text-emerald-400 flex items-center justify-center">
                        TESTS: PASS
                      </div>
                    </div>
                  </div>

                  {/* Audrey Avatar at Desk */}
                  {agentLocations.auditor?.zone === 'desk_auditor' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentClick('auditor');
                      }}
                      className="absolute -top-5 cursor-pointer hover:scale-110 transition-transform"
                    >
                      <AvatarCharacter
                        agentId="auditor"
                        state={agentLocations.auditor.state}
                        size={54}
                      />
                    </div>
                  )}
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Audrey Chen • QA & Compliance Auditor
                </div>
              </div>

              {/* CONFERENCE ROOM A ("Olympic Boardroom") */}
              <div
                onClick={() => setSelectedRoom('Olympic Boardroom A')}
                className="col-span-4 h-64 rounded-xl border-2 border-indigo-700/40 dark:border-indigo-500/30 bg-[#EEF2FF]/70 dark:bg-[#151A2C]/70 p-3 relative flex flex-col justify-between group hover:border-indigo-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-indigo-900/10 dark:border-indigo-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-indigo-900 dark:text-indigo-400">
                    Olympic Boardroom A
                  </span>
                  <span className="text-[9px] text-indigo-500 font-mono">10 Seats</span>
                </div>

                {/* Big Mahogany Conference Table + Strategy Screen */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-1">
                  {/* Presentation Smart Screen on Top Wall */}
                  <div className="w-36 h-4 bg-neutral-900 border border-indigo-400 rounded-b-xs text-[7px] font-mono text-cyan-300 flex items-center justify-center mb-1 shadow-xs">
                    Casa-Poki Roadmap & Performance
                  </div>

                  {/* Conference Table */}
                  <div className="w-48 h-20 rounded-full bg-[#4A2511] border-2 border-[#2E1508] shadow-lg relative flex items-center justify-center">
                    {/* Speakerphone puck in center */}
                    <div className="w-4 h-4 rounded-full bg-neutral-800 border border-neutral-600 flex items-center justify-center text-[7px] text-neutral-300">
                      🎙️
                    </div>

                    {/* Agent inside conference room if visiting */}
                    {Object.entries(agentLocations).map(([id, loc]) => {
                      if (loc.zone === 'boardroom') {
                        return (
                          <div
                            key={id}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAgentClick(id);
                            }}
                            className="absolute -top-3 cursor-pointer hover:scale-110 transition-transform"
                          >
                            <AvatarCharacter agentId={id} state={loc.state} size={48} />
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>

                  {/* Surrounding Swivel Chairs */}
                  <div className="flex justify-between w-44 mt-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="w-5 h-5 rounded-full bg-neutral-800 border border-neutral-600 shadow-xs" />
                    ))}
                  </div>
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center">
                  Glass Whiteboard • Interactive Strategy Sessions
                </div>
              </div>

              {/* BREAKOUT PODS (Focus Pod A & B) */}
              <div className="col-span-2 h-64 flex flex-col gap-2">
                {/* Pod A */}
                <div
                  onClick={() => setSelectedRoom('Breakout Focus Pod A')}
                  className="flex-1 rounded-xl border-2 border-violet-700/30 bg-[#F5F3FF]/70 dark:bg-[#1C182A]/70 p-2 flex flex-col justify-between hover:border-violet-400 transition-colors"
                >
                  <div className="text-[9px] font-mono font-bold text-violet-800 dark:text-violet-400 uppercase">
                    Focus Pod A
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-violet-300 dark:bg-violet-900 border border-violet-500 shadow-xs" />
                    <div className="w-4 h-4 rounded-full bg-amber-100 dark:bg-neutral-800 text-[8px] flex items-center justify-center">
                      ☕
                    </div>
                  </div>
                  <div className="text-[8px] text-neutral-400 text-center">Acoustic Glass</div>
                </div>

                {/* Pod B */}
                <div
                  onClick={() => setSelectedRoom('Breakout Focus Pod B')}
                  className="flex-1 rounded-xl border-2 border-violet-700/30 bg-[#F5F3FF]/70 dark:bg-[#1C182A]/70 p-2 flex flex-col justify-between hover:border-violet-400 transition-colors"
                >
                  <div className="text-[9px] font-mono font-bold text-violet-800 dark:text-violet-400 uppercase">
                    Focus Pod B
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-violet-300 dark:bg-violet-900 border border-violet-500 shadow-xs" />
                  </div>
                  <div className="text-[8px] text-neutral-400 text-center">1-on-1 Nook</div>
                </div>
              </div>

              {/* ROOM 106: Market Valuation & CMA Lab (Carter Hayes) */}
              <div
                onClick={() => setSelectedRoom('Room 106: Market Valuation & CMA Lab')}
                className="col-span-3 h-64 rounded-xl border-2 border-purple-800/40 dark:border-purple-600/30 bg-[#FAF5FF]/70 dark:bg-[#201529]/70 p-3 relative flex flex-col justify-between group hover:border-purple-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-purple-900/10 dark:border-purple-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-purple-900 dark:text-purple-400">
                    Room 106 • CMA Lab
                  </span>
                  <span className="text-[9px] text-purple-500 font-mono">NWMLS</span>
                </div>

                {/* Blueprint Table & Map Pins */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  {/* Large Architectural Blueprint Desk */}
                  <div className="w-34 h-20 rounded-lg bg-[#2E3B55] border-2 border-[#1E293B] shadow-md relative flex flex-col items-center justify-center p-2">
                    {/* King County Map with Pins */}
                    <div className="w-20 h-10 bg-sky-950 rounded-xs border border-sky-400 flex items-center justify-center relative">
                      <span className="text-[6px] text-sky-200 font-mono">King County</span>
                      <span className="absolute top-1 left-2 w-1.5 h-1.5 rounded-full bg-red-500" title="Bellevue" />
                      <span className="absolute bottom-2 right-3 w-1.5 h-1.5 rounded-full bg-amber-400" title="Renton" />
                    </div>
                  </div>

                  {/* Carter Avatar at Desk */}
                  {agentLocations.cma?.zone === 'desk_cma' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentClick('cma');
                      }}
                      className="absolute -top-5 cursor-pointer hover:scale-110 transition-transform"
                    >
                      <AvatarCharacter
                        agentId="cma"
                        state={agentLocations.cma.state}
                        size={54}
                      />
                    </div>
                  )}
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Carter Hayes • CMA & Valuation Specialist
                </div>
              </div>

            </div>

            {/* BOTTOM ROW: RECEPTION LOBBY + KITCHEN CAFÉ + LEISURE LOUNGE */}
            <div className="grid grid-cols-12 gap-3">
              
              {/* RECEPTION & INTAKE LOBBY (Miles Miller) */}
              <div
                onClick={() => setSelectedRoom('Front Reception & Visitor Intake')}
                className="col-span-3 h-60 rounded-xl border-2 border-blue-800/40 dark:border-blue-600/30 bg-[#F0F9FF]/70 dark:bg-[#13222D]/70 p-3 relative flex flex-col justify-between group hover:border-blue-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-blue-900/10 dark:border-blue-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-900 dark:text-blue-400">
                    Lobby • Intake & Webhooks
                  </span>
                  <span className="text-[9px] text-blue-500 font-mono">Guest Gate</span>
                </div>

                {/* Reception Counter & Visitor Kiosk */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-1">
                  {/* Curved Reception Counter */}
                  <div className="w-36 h-18 rounded-t-2xl rounded-b-lg bg-[#E0E7FF] dark:bg-[#1E293B] border-2 border-blue-300 dark:border-blue-700 shadow-md relative flex flex-col items-center justify-center p-2">
                    {/* Visitor iPad Stand */}
                    <div className="absolute top-1 right-2 flex items-center gap-1">
                      <div className="w-4 h-6 rounded-xs bg-black border border-white flex items-center justify-center text-[5px] text-cyan-300 font-mono" title="Open House Check-in iPad">
                        iPad
                      </div>
                    </div>
                    {/* Telephone & Inbound Mail Tray */}
                    <div className="absolute bottom-1 left-2 flex gap-0.5">
                      <div className="w-3 h-2 bg-neutral-700 rounded-xs" title="Telephone" />
                      <div className="w-2 h-2 bg-amber-200 rounded-xs" title="Mail" />
                    </div>
                  </div>

                  {/* Miles Avatar at Counter */}
                  {agentLocations.intake?.zone === 'desk_intake' && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentClick('intake');
                      }}
                      className="absolute -top-5 cursor-pointer hover:scale-110 transition-transform"
                    >
                      <AvatarCharacter
                        agentId="intake"
                        state={agentLocations.intake.state}
                        size={54}
                      />
                    </div>
                  )}
                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Miles Miller • Intake & Communications
                </div>
              </div>

              {/* CAFÉ & KITCHEN BREAKROOM */}
              <div
                onClick={() => setSelectedRoom('Café & Kitchen Breakroom')}
                className="col-span-4 h-60 rounded-xl border-2 border-amber-800/40 dark:border-amber-600/30 bg-[#FFFBEB]/70 dark:bg-[#201B11]/70 p-3 relative flex flex-col justify-between group hover:border-amber-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-amber-900/10 dark:border-amber-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-900 dark:text-amber-400 flex items-center gap-1">
                    <Coffee className="w-3 h-3 text-amber-500" />
                    Café & Kitchen Breakroom
                  </span>
                  <span className="text-[9px] text-amber-600 font-mono">Espresso Bar</span>
                </div>

                {/* Kitchen Counter, Espresso Machine, Watercooler & Visiting Agents */}
                <div className="flex-1 flex items-center justify-between px-2 mt-2 relative">
                  
                  {/* Left: Refrigerator & Snack Counter */}
                  <div className="flex flex-col items-center">
                    {/* Retro SMEG Refrigerator */}
                    <div className="w-9 h-22 rounded-t-lg bg-red-600 border border-red-800 shadow-md p-1 flex flex-col justify-between">
                      <div className="w-1 h-3 bg-neutral-200 rounded-full" />
                      <div className="w-1 h-3 bg-neutral-200 rounded-full" />
                    </div>
                    <span className="text-[7px] text-neutral-400 mt-0.5">SMEG</span>
                  </div>

                  {/* Center: Espresso Island Bar */}
                  <div className="flex flex-col items-center relative">
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        triggerEspresso();
                      }}
                      className="w-24 h-16 rounded-lg bg-neutral-100 dark:bg-neutral-800 border-2 border-neutral-300 dark:border-neutral-700 shadow-md flex flex-col items-center justify-center p-1 cursor-pointer hover:border-amber-400 transition-colors"
                      title="Click to brew espresso"
                    >
                      {/* Espresso Machine */}
                      <div className="w-10 h-7 rounded bg-neutral-900 border border-amber-500 relative flex items-center justify-center">
                        <div className="w-2 h-1 bg-amber-400 rounded-xs" />
                        {/* Steam Animation FX */}
                        {steamActive && (
                          <div className="absolute -top-3 flex gap-0.5 animate-bounce">
                            <span className="text-[9px]">♨️</span>
                          </div>
                        )}
                      </div>
                      <span className="text-[7px] font-mono text-amber-600 dark:text-amber-400 mt-1">
                        {steamActive ? 'Brewing...' : 'Italian Espresso'}
                      </span>
                    </div>

                    {/* Agents visiting kitchen café */}
                    <div className="flex items-center gap-1 absolute -top-5">
                      {Object.entries(agentLocations).map(([id, loc]) => {
                        if (loc.zone === 'kitchen_cafe') {
                          return (
                            <div
                              key={id}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAgentClick(id);
                              }}
                              className="cursor-pointer hover:scale-110 transition-transform"
                            >
                              <AvatarCharacter agentId={id} state={loc.state} size={48} />
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  </div>

                  {/* Right: Watercooler */}
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      triggerWatercooler();
                    }}
                    className="flex flex-col items-center cursor-pointer hover:scale-105 transition-transform"
                    title="Click for watercooler bubbles"
                  >
                    <div className="w-7 h-10 rounded-t-full bg-sky-400/80 border border-sky-600 relative flex items-center justify-center shadow-xs">
                      {waterBubbles && (
                        <div className="text-[7px] animate-bounce">🫧</div>
                      )}
                    </div>
                    <div className="w-8 h-10 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-b flex items-center justify-center">
                      <span className="text-[6px] text-sky-500">H2O</span>
                    </div>
                  </div>

                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center">
                  Fresh Espresso • Organic Snacks • Watercooler
                </div>
              </div>

              {/* LEISURE & WELLNESS LOUNGE */}
              <div
                onClick={() => setSelectedRoom('Leisure & Wellness Lounge')}
                className="col-span-5 h-60 rounded-xl border-2 border-emerald-800/40 dark:border-emerald-600/30 bg-[#F4F9F6]/70 dark:bg-[#14231A]/70 p-3 relative flex flex-col justify-between group hover:border-emerald-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-emerald-900/10 dark:border-emerald-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-400">
                    Leisure Lounge & Library
                  </span>
                  <span className="text-[9px] text-emerald-600 font-mono">Rest & Recovery</span>
                </div>

                {/* Sectional Velvet Sofa, Coffee Table & Potted Monstera */}
                <div className="flex-1 flex items-center justify-between px-4 mt-1 relative">
                  
                  {/* Left: Designer Monstera Plant */}
                  <div className="flex flex-col items-center" title="Monstera Deliciosa">
                    <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm shadow-xs">
                      🪴
                    </div>
                    <span className="text-[7px] text-neutral-400 mt-0.5">Monstera</span>
                  </div>

                  {/* Center: Plush Sectional Sofa */}
                  <div className="flex flex-col items-center relative">
                    <div className="w-56 h-18 rounded-xl bg-[#2D4A3E] border-2 border-[#1E332A] shadow-md flex flex-col items-center justify-center relative p-1">
                      {/* Modern Glass Coffee Table in front */}
                      <div className="w-28 h-6 rounded bg-neutral-200/90 dark:bg-neutral-800/90 border border-neutral-300 dark:border-neutral-700 flex items-center justify-center gap-2">
                        <span className="text-[6px] font-mono text-neutral-500">Architectural Digest</span>
                      </div>
                    </div>

                    {/* Agents relaxing on the sofa */}
                    <div className="flex items-center gap-2 absolute -top-5">
                      {Object.entries(agentLocations).map(([id, loc]) => {
                        if (loc.zone === 'lounge_sofa' || loc.zone === 'watercooler') {
                          return (
                            <div
                              key={id}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAgentClick(id);
                              }}
                              className="cursor-pointer hover:scale-110 transition-transform"
                            >
                              <AvatarCharacter agentId={id} state={loc.state} size={48} />
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  </div>

                  {/* Right: Modern Floor Lamp */}
                  <div className="flex flex-col items-center">
                    <div className="w-4 h-4 rounded-full bg-amber-300 border border-amber-500 shadow-sm" title="Warm Ambient Floor Lamp" />
                    <div className="w-0.5 h-14 bg-neutral-400" />
                  </div>

                </div>

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center">
                  Acoustic Rug • Velvet Lounge Sofa • Real Estate Periodicals
                </div>
              </div>

            </div>

          </div>
        </div>

        {/* Selected Room / Agent Interactive Flyout Drawer */}
        {(selectedRoom || activeAgentId) && (
          <div className="mt-4 p-4 rounded-xl bg-indigo-50/90 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all">
            
            <div className="flex items-center gap-3">
              {activeAgentId ? (
                <div className="w-12 h-12 flex-shrink-0">
                  <AvatarCharacter
                    agentId={activeAgentId}
                    state={agentLocations[activeAgentId]?.state || 'idle'}
                    size={48}
                  />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-xl bg-white dark:bg-charcoal border border-neutral-200 dark:border-neutral-700 flex items-center justify-center text-indigo-500">
                  <Building className="w-5 h-5" />
                </div>
              )}

              <div>
                <h4 className="font-serif font-bold text-sm text-neutral-900 dark:text-white">
                  {activeAgentId
                    ? agentStateMap[activeAgentId]?.name || activeAgentId
                    : selectedRoom}
                </h4>
                <p className="text-xs text-neutral-600 dark:text-neutral-300 mt-0.5">
                  {activeAgentId ? (
                    <>
                      <strong>Location:</strong> {agentLocations[activeAgentId]?.locationLabel} •{' '}
                      <em>{agentLocations[activeAgentId]?.activity}</em>
                    </>
                  ) : (
                    'Click any desk or agent to inspect live tasks, current activity, or assign requests.'
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {activeAgentId && onOpenChat && (
                <button
                  type="button"
                  onClick={() => onOpenChat(activeAgentId)}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors flex items-center gap-1.5 shadow-xs"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Chat with {agentStateMap[activeAgentId]?.name?.split(' ')[0] || 'Agent'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  setSelectedRoom(null);
                  setActiveAgentId(null);
                }}
                className="px-2.5 py-1.5 rounded-lg text-xs text-neutral-500 hover:text-neutral-800 dark:hover:text-white"
              >
                Dismiss
              </button>
            </div>

          </div>
        )}

      </div>

      {/* Map Legend */}
      <div className="flex items-center justify-between text-[11px] text-neutral-500 px-2 flex-wrap gap-2">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Working at Desk
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Coffee Break in Kitchen
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> Relaxing in Lounge
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" /> Olympic Boardroom
          </span>
        </div>
        <div className="flex items-center gap-1 text-neutral-400">
          <span>Tip: Click on the Espresso machine or Server Rack for live interactions!</span>
        </div>
      </div>
    </div>
  );
}
