import React, { useState, useEffect, useMemo } from 'react';
import IsometricCharacter from './IsometricCharacter';
import {
  Coffee,
  Server,
  Printer,
  Sparkles,
  MessageSquare,
  ZoomIn,
  ZoomOut,
  Compass,
  RotateCw,
  Users,
  CheckCircle2
} from 'lucide-react';

export default function IsometricOfficeFloor({
  agents = [],
  recentFlows = [],
  containers = [],
  monitors = [],
  onSelectAgent,
  onOpenChat,
}) {
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [printerActive, setPrinterActive] = useState(false);
  const [coffeeRefreshed, setCoffeeRefreshed] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [simTick, setSimTick] = useState(0);

  // Deterministic simulation ticker to rotate idle behaviors every 18 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setSimTick((t) => t + 1);
    }, 18000);
    return () => clearInterval(timer);
  }, []);

  const agentStateMap = useMemo(() => {
    const map = {};
    agents.forEach((a) => {
      map[a.id] = a;
    });
    return map;
  }, [agents]);

  // Compute positions & animation modes for each agent matching the reference image layout
  const simulationLayout = useMemo(() => {
    // 7 Agents: Marcus, Ian, Audrey, Miles, Fiona, Maya, Carter
    const layout = {};

    // Check which agents are actively processing tasks
    const activeIds = agents.filter((a) => a.status === 'active').map((a) => a.id);

    // Baseline desk positions:
    // Pod Top-Left: Maya (Drawing Tablet Desk)
    // Pod Top-Right: Marcus (Executive Planning Desk)
    // Pod Bottom-Left: Carter (CMA Valuation Desk) + Audrey (Auditor Pairing)
    // Pod Bottom-Right: Ian (Tech & DevOps Desk)
    // Intake Desk: Miles
    // Finance Desk: Fiona

    // 1. MAYA (Creative / Marketing)
    if (activeIds.includes('marketing')) {
      layout.marketing = {
        pos: { x: 260, y: 310 },
        animation: 'working_tablet',
        label: 'Creative Workstation',
        activity: 'Designing open house flyers on graphics tablet',
      };
    } else if (simTick % 3 === 0) {
      layout.marketing = {
        pos: { x: 260, y: 310 },
        animation: 'working_tablet',
        label: 'Creative Workstation',
        activity: 'Sketching brand assets on tablet',
      };
    } else {
      layout.marketing = {
        pos: { x: 740, y: 640 },
        animation: 'leisure_coffee',
        label: 'Round Meeting Table',
        activity: 'Enjoying coffee & glazed donut with team ☕🍩',
      };
    }

    // 2. MARCUS (Manager / Orchestrator)
    if (activeIds.includes('manager')) {
      layout.manager = {
        pos: { x: 710, y: 240 },
        animation: 'working_typing',
        label: 'Executive Workstation',
        activity: 'Orchestrating multi-agent pipeline & reviewing tools',
      };
    } else if (simTick % 2 === 0) {
      layout.manager = {
        pos: { x: 710, y: 240 },
        animation: 'working_typing',
        label: 'Executive Workstation',
        activity: 'Reviewing quarterly real estate performance',
      };
    } else {
      // Meeting in hallway with Carter
      layout.manager = {
        pos: { x: 490, y: 470 },
        animation: 'meeting_left',
        label: 'Central Hallway Standup',
        activity: 'Reviewing property disclosure packets with Carter 📋',
      };
    }

    // 3. CARTER (CMA / Real Estate Specialist)
    if (activeIds.includes('cma')) {
      layout.cma = {
        pos: { x: 380, y: 680 },
        animation: 'working_typing',
        label: 'CMA Valuation Desk',
        activity: 'Crunching NWMLS comps for Eastside properties',
      };
    } else if (layout.manager?.animation === 'meeting_left') {
      layout.cma = {
        pos: { x: 550, y: 470 },
        animation: 'meeting_right',
        label: 'Central Hallway Standup',
        activity: 'Discussing Northwest market pricing with Marcus 🗣️',
      };
    } else {
      layout.cma = {
        pos: { x: 380, y: 680 },
        animation: 'working_typing',
        label: 'CMA Valuation Desk',
        activity: 'Inspecting King County parcel maps',
      };
    }

    // 4. AUDREY (QA & Compliance Auditor)
    if (activeIds.includes('auditor')) {
      layout.auditor = {
        pos: { x: 330, y: 640 },
        animation: 'pairing_stand',
        label: 'Valuation Pod (Over-the-Shoulder)',
        activity: 'Auditing tool execution schemas & safety compliance',
      };
    } else if (simTick % 3 === 1) {
      // Walking in hallway carrying audit folder (matching walking lady in reference!)
      layout.auditor = {
        pos: { x: 840, y: 340 },
        animation: 'walking',
        label: 'Corridor Walkway',
        activity: 'Delivering audited reports across the open floor 📂',
      };
    } else {
      layout.auditor = {
        pos: { x: 330, y: 640 },
        animation: 'pairing_stand',
        label: 'Valuation Pod (Pairing)',
        activity: 'Assisting Carter with verified CMA audit figures',
      };
    }

    // 5. IAN (IT Systems & DevOps Guardian)
    if (activeIds.includes('it')) {
      layout.it = {
        pos: { x: 670, y: 220 },
        animation: 'working_typing',
        label: 'DevOps & Telemetry Station',
        activity: 'Inspecting Docker containers & Uptime Kuma alerts',
      };
    } else if (simTick % 4 === 0) {
      layout.it = {
        pos: { x: 790, y: 670 },
        animation: 'leisure_coffee',
        label: 'Round Meeting Table',
        activity: 'Recharging with an espresso at the break table ☕',
      };
    } else {
      layout.it = {
        pos: { x: 670, y: 220 },
        animation: 'working_typing',
        label: 'DevOps & Telemetry Station',
        activity: 'Auditing 17 container heartbeats & ZFS storage',
      };
    }

    // 6. MILES (Intake & Communications)
    if (activeIds.includes('intake')) {
      layout.intake = {
        pos: { x: 500, y: 530 },
        animation: 'walking',
        label: 'Front Walkway',
        activity: 'Ingesting visitor check-ins into Twenty CRM',
      };
    } else if (simTick % 2 === 1) {
      layout.intake = {
        pos: { x: 760, y: 620 },
        animation: 'leisure_coffee',
        label: 'Round Meeting Table',
        activity: 'Taking a quick break at the coffee table ☕',
      };
    } else {
      layout.intake = {
        pos: { x: 510, y: 490 },
        animation: 'walking',
        label: 'Central Walkway',
        activity: 'Walking to intake kiosk with visitor clipboard 📋',
      };
    }

    // 7. FIONA (Financial Controller)
    if (activeIds.includes('finance')) {
      layout.finance = {
        pos: { x: 650, y: 700 },
        animation: 'leisure_coffee',
        label: 'Round Meeting Table',
        activity: 'Reconciling bank accounts with Actual Budget',
      };
    } else {
      layout.finance = {
        pos: { x: 650, y: 700 },
        animation: 'leisure_coffee',
        label: 'Round Meeting Table',
        activity: 'Balancing financial statements over coffee ☕',
      };
    }

    return layout;
  }, [agents, simTick]);

  const handleAgentClick = (agentId) => {
    setSelectedAgentId(agentId);
    const ag = agentStateMap[agentId];
    if (onSelectAgent && ag) {
      onSelectAgent(ag);
    }
  };

  const triggerPrinter = () => {
    setPrinterActive(true);
    setTimeout(() => setPrinterActive(false), 5000);
  };

  const triggerCoffee = () => {
    setCoffeeRefreshed(true);
    setTimeout(() => setCoffeeRefreshed(false), 4000);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Control Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-serif font-bold text-neutral-800 dark:text-neutral-200">
            <Compass className="w-4 h-4 text-lime-600 dark:text-lime-400" />
            <span>Open Space Architectural Floor (2.5D Isometric)</span>
          </div>
          <span className="hidden sm:inline text-neutral-400">•</span>
          <span className="hidden sm:inline text-neutral-500 text-[11px]">
            Live Multi-State Agent Simulation: Working, Walking, Meetings & Break Lounge
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Zoom */}
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

          {/* Interactive Printer Action */}
          <button
            type="button"
            onClick={triggerPrinter}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border flex items-center gap-1.5 transition-all ${
              printerActive
                ? 'bg-blue-100 text-blue-900 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-700 animate-pulse'
                : 'bg-neutral-50 dark:bg-charcoal border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-blue-400'
            }`}
            title="Print test flyer"
          >
            <Printer className="w-3.5 h-3.5 text-blue-500" />
            <span>{printerActive ? 'Printing...' : 'Print Doc'}</span>
          </button>

          {/* Refresh Coffee */}
          <button
            type="button"
            onClick={triggerCoffee}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border flex items-center gap-1.5 transition-all ${
              coffeeRefreshed
                ? 'bg-lime-100 text-lime-900 border-lime-300 dark:bg-lime-950 dark:text-lime-300 dark:border-lime-700 animate-pulse'
                : 'bg-neutral-50 dark:bg-charcoal border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-lime-500'
            }`}
            title="Refresh donuts & coffee on round table"
          >
            <Coffee className="w-3.5 h-3.5 text-lime-600 dark:text-lime-400" />
            <span>{coffeeRefreshed ? 'Fresh Batch!' : 'Coffee & Donuts'}</span>
          </button>
        </div>
      </div>

      {/* Main Isometric Floor Stage */}
      <div className="relative rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden p-4 sm:p-6 transition-all">
        <div
          className="overflow-x-auto pb-4 transition-transform origin-top-left"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          {/* Isometric Container Box */}
          <div className="min-w-[1020px] max-w-[1140px] mx-auto relative rounded-xl border-4 border-neutral-700/60 dark:border-neutral-700/80 bg-[#EEEEEE] dark:bg-[#18191C] shadow-inner overflow-hidden">
            
            {/* SVG Isometric Canvas (1000 x 850) */}
            <svg
              viewBox="0 0 1000 850"
              className="w-full h-auto select-none"
              style={{ minHeight: '750px' }}
            >
              <defs>
                {/* Isometric Grid Tile Pattern */}
                <pattern id="isoGrid" width="60" height="34.64" patternUnits="userSpaceOnUse">
                  <path
                    d="M 30 0 L 60 17.32 L 30 34.64 L 0 17.32 Z"
                    fill="none"
                    stroke="rgba(160, 160, 160, 0.25)"
                    strokeWidth="1"
                  />
                  <line x1="0" y1="17.32" x2="60" y2="17.32" stroke="rgba(160, 160, 160, 0.15)" strokeWidth="0.8" />
                </pattern>

                {/* Drop shadow for furniture */}
                <filter id="deskShadow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="3" dy="6" stdDeviation="4" floodOpacity="0.18" />
                </filter>
                <filter id="chairShadow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="2" dy="4" stdDeviation="3" floodOpacity="0.15" />
                </filter>
              </defs>

              {/* 1. Tiled Floor Base */}
              <rect width="1000" height="850" fill="#E8E8E8" />
              <rect width="1000" height="850" fill="url(#isoGrid)" />

              {/* Title Header Stamp */}
              <text
                x="45"
                y="60"
                fontFamily="Plus Jakarta Sans, sans-serif"
                fontWeight="800"
                fontSize="24"
                fill="#EF4444"
                letterSpacing="1"
                opacity="0.85"
              >
                OPEN SPACE
              </text>
              <text
                x="185"
                y="80"
                fontFamily="Playfair Display, Georgia, serif"
                fontStyle="italic"
                fontSize="22"
                fill="#18181B"
                opacity="0.75"
              >
                office
              </text>

              {/* =====================================================================
                  2. POD 1 (TOP-LEFT): CREATIVE & MARKETING WORKSTATION (MAYA)
                  ===================================================================== */}
              <g id="pod_top_left">
                {/* Curved Chartreuse / Lime Acoustic Partition Divider */}
                <path
                  d="M 120 330 C 120 220, 180 180, 290 180 L 375 125"
                  fill="none"
                  stroke="#9ACD32"
                  strokeWidth="28"
                  strokeLinecap="round"
                  filter="url(#deskShadow)"
                />
                <path
                  d="M 120 330 C 120 220, 180 180, 290 180 L 375 125"
                  fill="none"
                  stroke="#84CC16"
                  strokeWidth="24"
                  strokeLinecap="round"
                />

                {/* Modular White Workstation Desk */}
                <g filter="url(#deskShadow)">
                  {/* Desktop Surface (Isometric Polygon) */}
                  <polygon points="140,250 250,185 335,235 225,300" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1.5" />
                  {/* Desk Front Panel / Drawers */}
                  <polygon points="140,250 225,300 225,340 140,290" fill="#F1F5F9" stroke="#CBD5E1" strokeWidth="1" />
                  <polygon points="225,300 335,235 335,275 225,340" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" />
                  {/* Under-desk Drawer Pulls */}
                  <line x1="215" y1="315" x2="222" y2="319" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
                  <line x1="215" y1="325" x2="222" y2="329" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
                </g>

                {/* Desktop Props on Maya's Desk */}
                {/* Monitor with Stand */}
                <polygon points="180,225 220,202 220,220 180,243" fill="#18181B" />
                <polygon points="183,227 217,207 217,218 183,238" fill="#EF4444" opacity="0.8" />
                <rect x="198" y="238" width="4" height="6" fill="#71717A" />

                {/* Angled Graphics Drawing Tablet on desk */}
                <polygon points="238,245 285,218 310,233 263,260" fill="#18181B" stroke="#A855F7" strokeWidth="1.2" />
                <polygon points="242,246 281,223 304,236 265,258" fill="#F59E0B" />

                {/* Office Swivel Chair for Maya */}
                <g filter="url(#chairShadow)">
                  <ellipse cx="320" cy="305" rx="14" ry="9" fill="#18181B" />
                  <path d="M 315 285 Q 330 275 335 295 L 325 315 Z" fill="#27272A" />
                  {/* 5-Star Chair Caster Base */}
                  <line x1="320" y1="312" x2="310" y2="322" stroke="#52525B" strokeWidth="2.5" />
                  <line x1="320" y1="312" x2="330" y2="322" stroke="#52525B" strokeWidth="2.5" />
                  <line x1="320" y1="312" x2="320" y2="326" stroke="#52525B" strokeWidth="2.5" />
                </g>
              </g>

              {/* =====================================================================
                  3. CENTRAL STORAGE CREDENZAS WITH SUCCULENT PLANTS & BINDERS
                  ===================================================================== */}
              <g id="central_credenza" filter="url(#deskShadow)">
                {/* Long White Storage Cabinet Top */}
                <polygon points="325,185 490,90 645,180 480,275" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1.5" />
                {/* Front Side of Cabinet */}
                <polygon points="480,275 645,180 645,260 480,355" fill="#F8FAFC" stroke="#CBD5E1" strokeWidth="1.5" />
                {/* Left Side of Cabinet */}
                <polygon points="325,185 480,275 480,355 325,265" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />

                {/* Cabinet Door Seams & Handles */}
                <line x1="415" y1="320" x2="415" y2="280" stroke="#CBD5E1" strokeWidth="1.5" />
                <circle cx="410" cy="300" r="2.5" fill="#64748B" />
                <circle cx="420" cy="300" r="2.5" fill="#64748B" />

                <line x1="560" y1="225" x2="560" y2="185" stroke="#CBD5E1" strokeWidth="1.5" />
                <circle cx="555" cy="205" r="2.5" fill="#64748B" />
                <circle cx="565" cy="205" r="2.5" fill="#64748B" />

                {/* Colorful Binders & Books on Top of Credenza */}
                {/* Stack of Books */}
                <polygon points="370,185 395,170 430,190 405,205" fill="#3B82F6" />
                <polygon points="370,180 395,165 430,185 405,200" fill="#E2E8F0" />
                <polygon points="370,175 395,160 430,180 405,195" fill="#A855F7" />

                {/* Potted Succulent Plants in Red Terracotta Pots */}
                <g transform="translate(440, 180)">
                  <ellipse cx="20" cy="18" rx="8" ry="4" fill="#C2410C" />
                  <polygon points="12,18 28,18 25,28 15,28" fill="#EA580C" />
                  {/* Green Succulent Foliage */}
                  <circle cx="16" cy="12" r="5" fill="#84CC16" />
                  <circle cx="24" cy="12" r="5" fill="#65A30D" />
                  <circle cx="20" cy="8" r="4.5" fill="#A3E635" />
                </g>

                <g transform="translate(485, 210)">
                  <ellipse cx="16" cy="15" rx="7" ry="3.5" fill="#C2410C" />
                  <polygon points="9,15 23,15 21,24 11,24" fill="#EA580C" />
                  <circle cx="13" cy="10" r="4.5" fill="#84CC16" />
                  <circle cx="19" cy="10" r="4.5" fill="#65A30D" />
                </g>

                {/* Trailing Potted Ivy Plant on corner */}
                <g transform="translate(345, 175)">
                  <circle cx="10" cy="10" r="6" fill="#15803D" />
                  <path d="M 10 12 Q 12 28 8 36" stroke="#22C55E" strokeWidth="2" fill="none" />
                  <circle cx="8" cy="24" r="3" fill="#4ADE80" />
                  <circle cx="9" cy="34" r="2.5" fill="#86EFAC" />
                </g>
              </g>

              {/* =====================================================================
                  4. HEAVY-DUTY OFFICE PRINTER / COPIER STATION
                  ===================================================================== */}
              <g
                id="office_printer"
                filter="url(#deskShadow)"
                onClick={triggerPrinter}
                className="cursor-pointer hover:opacity-90 transition-opacity"
              >
                {/* Printer Body */}
                <polygon points="480,95 550,55 610,90 540,130" fill="#3B82F6" />
                <polygon points="540,130 610,90 610,145 540,185" fill="#1D4ED8" />
                <polygon points="480,95 540,130 540,185 480,150" fill="#2563EB" />
                {/* Paper Output Tray & Lid */}
                <polygon points="515,68 565,40 600,60 550,88" fill="#F8FAFC" stroke="#CBD5E1" strokeWidth="1" />
                <polygon points="525,120 575,92 575,102 525,130" fill="#FFFFFF" />

                {/* Animated Printed Page emerging when active */}
                {printerActive && (
                  <g className="animate-bounce">
                    <polygon points="528,115 572,90 585,98 541,123" fill="#FEF08A" stroke="#CA8A04" strokeWidth="1" />
                    <text x="532" y="112" fontSize="6" fill="#854D0E" fontFamily="monospace">FLYER</text>
                  </g>
                )}
                <text x="548" y="165" fontSize="7" fill="#FFFFFF" fontFamily="monospace">CANON</text>
              </g>

              {/* =====================================================================
                  5. POD 2 (TOP-RIGHT): MANAGEMENT WORKSTATION (MARCUS VANCE)
                  ===================================================================== */}
              <g id="pod_top_right">
                {/* Chartreuse Acoustic Divider behind desk */}
                <path
                  d="M 580 180 L 740 85"
                  fill="none"
                  stroke="#9ACD32"
                  strokeWidth="24"
                  strokeLinecap="round"
                  filter="url(#deskShadow)"
                />
                <path
                  d="M 580 180 L 740 85"
                  fill="none"
                  stroke="#84CC16"
                  strokeWidth="20"
                  strokeLinecap="round"
                />

                {/* Desk Surface */}
                <g filter="url(#deskShadow)">
                  <polygon points="565,225 675,160 760,210 650,275" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1.5" />
                  <polygon points="650,275 760,210 760,250 650,315" fill="#F1F5F9" stroke="#CBD5E1" strokeWidth="1" />
                  <polygon points="565,225 650,275 650,315 565,265" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" />
                </g>

                {/* Dual Monitors on Marcus' Desk */}
                {/* Screen 1 */}
                <polygon points="585,190 625,167 625,188 585,211" fill="#18181B" />
                <polygon points="588,193 622,173 622,185 588,205" fill="#10B981" opacity="0.9" />
                {/* Screen 2 */}
                <polygon points="630,165 670,142 670,163 630,186" fill="#18181B" />
                <polygon points="633,168 667,148 667,160 633,180" fill="#3B82F6" opacity="0.9" />

                {/* Keyboard & Pen Cup */}
                <polygon points="615,220 650,200 665,208 630,228" fill="#3F3F46" />
                <cylinder cx="568" cy="225" r="3" fill="#18181B" />

                {/* Swivel Chair for Marcus */}
                <g filter="url(#chairShadow)">
                  <ellipse cx="715" cy="280" rx="14" ry="9" fill="#18181B" />
                  <path d="M 710 260 Q 725 250 730 270 L 720 290 Z" fill="#27272A" />
                  <line x1="715" y1="287" x2="705" y2="297" stroke="#52525B" strokeWidth="2.5" />
                  <line x1="715" y1="287" x2="725" y2="297" stroke="#52525B" strokeWidth="2.5" />
                </g>
              </g>

              {/* =====================================================================
                  6. POTTED PALM TREE IN PLANTER (NEXT TO CENTRAL CREDENZA)
                  ===================================================================== */}
              <g id="palm_tree" transform="translate(620, 360)" filter="url(#deskShadow)">
                {/* Ceramic Pot */}
                <ellipse cx="25" cy="65" rx="14" ry="7" fill="#3F3F46" />
                <polygon points="11,65 39,65 36,85 14,85" fill="#27272A" />
                <ellipse cx="25" cy="85" rx="11" ry="5.5" fill="#18181B" />
                {/* Palm Trunk */}
                <path d="M 25 65 Q 23 45 25 30" stroke="#78350F" strokeWidth="5" fill="none" strokeLinecap="round" />
                {/* Spreading Palm Fronds */}
                <path d="M 25 30 Q 5 15 -15 28" stroke="#65A30D" strokeWidth="4" fill="none" strokeLinecap="round" />
                <path d="M 25 30 Q 30 5 40 -8" stroke="#84CC16" strokeWidth="4" fill="none" strokeLinecap="round" />
                <path d="M 25 30 Q 45 20 65 30" stroke="#4D7C0F" strokeWidth="4" fill="none" strokeLinecap="round" />
                <path d="M 25 30 Q 5 35 -8 50" stroke="#84CC16" strokeWidth="3.5" fill="none" strokeLinecap="round" />
                <path d="M 25 30 Q 40 40 55 52" stroke="#65A30D" strokeWidth="3.5" fill="none" strokeLinecap="round" />
              </g>

              {/* =====================================================================
                  7. POD 3 (BOTTOM-LEFT): CMA & VALUATION POD (CARTER & AUDREY)
                  ===================================================================== */}
              <g id="pod_bottom_left">
                {/* Acoustic Partition Divider */}
                <path
                  d="M 80 600 L 80 730"
                  fill="none"
                  stroke="#9ACD32"
                  strokeWidth="24"
                  strokeLinecap="round"
                  filter="url(#deskShadow)"
                />
                <path
                  d="M 80 600 L 80 730"
                  fill="none"
                  stroke="#84CC16"
                  strokeWidth="20"
                  strokeLinecap="round"
                />

                {/* Low Credenza Shelf on Left */}
                <g filter="url(#deskShadow)">
                  <polygon points="95,595 190,540 280,592 185,647" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1.5" />
                  <polygon points="185,647 280,592 280,660 185,715" fill="#F8FAFC" stroke="#CBD5E1" strokeWidth="1.5" />
                  <polygon points="95,595 185,647 185,715 95,663" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />
                  {/* Binders inside open shelf */}
                  <rect x="110" y="660" width="16" height="24" rx="2" fill="#EF4444" />
                  <rect x="130" y="650" width="16" height="24" rx="2" fill="#3B82F6" />
                  <polygon points="210,610 240,593 260,605 230,622" fill="#18181B" title="Laptop on shelf" />
                </g>

                {/* Carter's Workstation Desk */}
                <g filter="url(#deskShadow)">
                  <polygon points="265,650 375,585 460,635 350,700" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1.5" />
                  <polygon points="350,700 460,635 460,675 350,740" fill="#F1F5F9" stroke="#CBD5E1" strokeWidth="1" />
                  <polygon points="265,650 350,700 350,740 265,690" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" />
                </g>

                {/* Desk Blueprint & Monitor */}
                <polygon points="275,642 320,616 345,630 300,656" fill="#38BDF8" stroke="#0284C7" strokeWidth="1" title="Blueprints" />
                <polygon points="330,620 370,597 370,618 330,641" fill="#18181B" />
                <polygon points="333,623 367,603 367,615 333,635" fill="#0284C7" opacity="0.9" />

                {/* Swivel Chair */}
                <g filter="url(#chairShadow)">
                  <ellipse cx="400" cy="710" rx="14" ry="9" fill="#18181B" />
                  <path d="M 395 690 Q 410 680 415 700 L 405 720 Z" fill="#27272A" />
                </g>
              </g>

              {/* =====================================================================
                  8. CENTRAL COLLABORATION & LEISURE ROUND TABLE (COFFEE & DONUTS!)
                  ===================================================================== */}
              <g
                id="round_collaboration_table"
                filter="url(#deskShadow)"
                onClick={triggerCoffee}
                className="cursor-pointer hover:opacity-95 transition-opacity"
              >
                {/* Large Lime-Green Circular Table Surface */}
                <ellipse cx="735" cy="635" rx="90" ry="52" fill="#A3C639" stroke="#84CC16" strokeWidth="3" />
                {/* 4 Sturdy Black Metal Legs */}
                <line x1="660" y1="655" x2="660" y2="725" stroke="#18181B" strokeWidth="4" strokeLinecap="round" />
                <line x1="810" y1="655" x2="810" y2="725" stroke="#18181B" strokeWidth="4" strokeLinecap="round" />
                <line x1="735" y1="685" x2="735" y2="755" stroke="#18181B" strokeWidth="4.5" strokeLinecap="round" />

                {/* Centerpiece Succulent Plant in Black Pot */}
                <ellipse cx="735" cy="625" rx="12" ry="7" fill="#18181B" />
                <circle cx="731" cy="619" r="6" fill="#4D7C0F" />
                <circle cx="739" cy="619" r="6" fill="#65A30D" />
                <circle cx="735" cy="614" r="5" fill="#84CC16" />

                {/* Plate Filled with Fresh Donuts / Pastries */}
                <g transform="translate(800, 645)">
                  <ellipse cx="0" cy="0" rx="14" ry="8" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1" />
                  {/* Chocolate Donut with Sprinkles */}
                  <ellipse cx="-4" cy="-1" rx="5" ry="3" fill="#78350F" />
                  <circle cx="-4" cy="-1" r="1.5" fill="#FFFFFF" />
                  {/* Glazed Donut */}
                  <ellipse cx="4" cy="1" rx="5" ry="3" fill="#F59E0B" />
                  <circle cx="4" cy="1" r="1.5" fill="#FFFFFF" />
                  {/* Pink Frosted Donut */}
                  <ellipse cx="1" cy="-3" rx="4.5" ry="2.5" fill="#F43F5E" />
                </g>

                {/* Coffee Cups on the Table with Rising Steam */}
                {/* Cup 1 */}
                <g transform="translate(660, 620)">
                  <ellipse cx="0" cy="0" rx="9" ry="5" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1" />
                  <ellipse cx="0" cy="-1" rx="6" ry="3.5" fill="#451A03" />
                  {coffeeRefreshed && (
                    <path d="M 0 -4 Q 2 -10 0 -16" stroke="#FFFFFF" strokeWidth="1.5" fill="none" className="animate-bounce" />
                  )}
                </g>
                {/* Cup 2 */}
                <g transform="translate(785, 595)">
                  <ellipse cx="0" cy="0" rx="6" ry="3.5" fill="#FFFFFF" stroke="#D1D5DB" strokeWidth="1" />
                  <ellipse cx="0" cy="-1" rx="4" ry="2" fill="#451A03" />
                  <text x="-4" y="1" fontSize="4" fill="#78350F">☕</text>
                </g>
                {/* Cup 3 */}
                <g transform="translate(775, 615)">
                  <ellipse cx="0" cy="0" rx="6" ry="3.5" fill="#FFFFFF" stroke="#D1D5DB" strokeWidth="1" />
                  <ellipse cx="0" cy="-1" rx="4" ry="2" fill="#451A03" />
                </g>

                {/* 4 Ergonomic Swivel Chairs Around the Table */}
                {/* Chair West */}
                <g filter="url(#chairShadow)" transform="translate(605, 590)">
                  <ellipse cx="0" cy="10" rx="14" ry="9" fill="#18181B" />
                  <path d="M -8 -15 Q 10 -25 15 -5 L 5 15 Z" fill="#27272A" />
                  <line x1="0" y1="17" x2="-8" y2="28" stroke="#52525B" strokeWidth="2.5" />
                  <line x1="0" y1="17" x2="8" y2="28" stroke="#52525B" strokeWidth="2.5" />
                </g>
                {/* Chair East */}
                <g filter="url(#chairShadow)" transform="translate(865, 630)">
                  <ellipse cx="0" cy="10" rx="14" ry="9" fill="#18181B" />
                  <path d="M -15 -15 Q 5 -25 10 -5 L 0 15 Z" fill="#27272A" />
                  <line x1="0" y1="17" x2="-8" y2="28" stroke="#52525B" strokeWidth="2.5" />
                  <line x1="0" y1="17" x2="8" y2="28" stroke="#52525B" strokeWidth="2.5" />
                </g>
                {/* Chair South */}
                <g filter="url(#chairShadow)" transform="translate(655, 750)">
                  <ellipse cx="0" cy="10" rx="14" ry="9" fill="#18181B" />
                  <path d="M -15 -10 Q 0 -22 15 -10 L 10 12 Z" fill="#27272A" />
                  <line x1="0" y1="17" x2="-8" y2="28" stroke="#52525B" strokeWidth="2.5" />
                  <line x1="0" y1="17" x2="8" y2="28" stroke="#52525B" strokeWidth="2.5" />
                </g>
              </g>

              {/* =====================================================================
                  9. DYNAMIC ANIMATED CHARACTERS LAYER (PLACED ON ISOMETRIC COORDINATES)
                  ===================================================================== */}
              {Object.entries(simulationLayout).map(([agentId, config]) => {
                const isSelected = selectedAgentId === agentId;
                const liveStatus = agentStateMap[agentId]?.status || 'idle';
                const isBusy = liveStatus === 'active';

                return (
                  <foreignObject
                    key={agentId}
                    x={config.pos.x - 32}
                    y={config.pos.y - 70}
                    width="110"
                    height="130"
                    className="overflow-visible"
                  >
                    <div className="relative group flex flex-col items-center">
                      {/* Character Vector with Animation */}
                      <IsometricCharacter
                        agentId={agentId}
                        animation={config.animation}
                        scale={isSelected ? 1.15 : 1}
                        onClick={() => handleAgentClick(agentId)}
                      />

                      {/* Floating Name Badge */}
                      <div
                        onClick={() => handleAgentClick(agentId)}
                        className={`mt-1 px-2 py-0.5 rounded-full text-[9px] font-bold shadow-xs whitespace-nowrap cursor-pointer transition-transform ${
                          isBusy
                            ? 'bg-amber-100 text-amber-900 border border-amber-400 dark:bg-amber-950 dark:text-amber-200 animate-pulse'
                            : isSelected
                            ? 'bg-indigo-600 text-white'
                            : 'bg-white/90 dark:bg-neutral-800/90 text-neutral-800 dark:text-neutral-200 border border-neutral-300 dark:border-neutral-700 hover:border-lime-500'
                        }`}
                      >
                        {agentStateMap[agentId]?.name || agentId}
                        {isBusy && ' ⚡'}
                      </div>
                    </div>
                  </foreignObject>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Selected Agent Detailed Flyout Drawer */}
        {selectedAgentId && (
          <div className="mt-4 p-4 rounded-xl bg-lime-50/90 dark:bg-lime-950/40 border border-lime-300 dark:border-lime-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all">
            <div className="flex items-center gap-3">
              <div className="w-12 h-14 flex-shrink-0">
                <IsometricCharacter
                  agentId={selectedAgentId}
                  animation={simulationLayout[selectedAgentId]?.animation || 'working_typing'}
                  scale={0.9}
                />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-serif font-bold text-sm text-neutral-900 dark:text-white">
                    {agentStateMap[selectedAgentId]?.name || selectedAgentId}
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300">
                    {agentStateMap[selectedAgentId]?.role}
                  </span>
                </div>
                <p className="text-xs text-neutral-700 dark:text-neutral-300 mt-1">
                  <strong>Location:</strong> {simulationLayout[selectedAgentId]?.label} •{' '}
                  <span className="text-lime-800 dark:text-lime-300 font-medium">
                    {simulationLayout[selectedAgentId]?.activity}
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {onOpenChat && (
                <button
                  type="button"
                  onClick={() => onOpenChat(selectedAgentId)}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-xs"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Chat with {agentStateMap[selectedAgentId]?.name?.split(' ')[0] || 'Agent'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => setSelectedAgentId(null)}
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
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Working at Desk / Tablet
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Walking with Reports
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Hallway Document Meeting
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-lime-500" /> Round Table Coffee & Donuts
          </span>
        </div>
        <div className="flex items-center gap-1 text-neutral-400">
          <span>Tip: Click on the Round Table or Printer for live interactions!</span>
        </div>
      </div>
    </div>
  );
}
