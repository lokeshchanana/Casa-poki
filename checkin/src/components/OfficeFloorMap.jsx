import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import AvatarCharacter from './AvatarCharacter';
import {
  Coffee,
  Server,
  Activity,
  Users,
  MessageSquare,
  Sparkles,
  Info,
  ZoomIn,
  ZoomOut,
  Compass,
  Building,
  CheckCircle2,
  ArrowRight,
  Footprints,
  RotateCcw
} from 'lucide-react';

/**
 * Bellevue HQ Floor 4 Blueprint Coordinate Anchors (in % of canvas)
 * Row 1 (y: 0 - 31%): Suites 101, 102, 104, 105
 * North Promenade Hallway: y = 33.2%
 * Row 2 (y: 35.5 - 66.5%): Suites 103, Boardroom, Pods, 106
 * South Commons Hallway: y = 68.7%
 * Row 3 (y: 71.0 - 100%): Lobby, Kitchen Café, Leisure Lounge
 */
const FLOOR_ZONES = {
  desk_manager: { x: 12.5, y: 15.2, label: 'Suite 101 • Executive Desk', defaultState: 'idle' },
  desk_it: { x: 41.5, y: 15.2, label: 'Room 102 • DevOps Workstation', defaultState: 'idle' },
  desk_finance: { x: 62.5, y: 15.2, label: 'Room 104 • Finance Ledger Desk', defaultState: 'idle' },
  desk_marketing: { x: 87.5, y: 15.2, label: 'Room 105 • Creative Drafting Desk', defaultState: 'idle' },

  desk_auditor: { x: 12.5, y: 51.0, label: 'Room 103 • QA & Compliance Pod', defaultState: 'idle' },
  boardroom: { x: 41.7, y: 51.0, label: 'Olympic Boardroom A', defaultState: 'chatting' },
  breakout_pods: { x: 66.7, y: 51.0, label: 'Breakout Focus Pod', defaultState: 'chatting' },
  desk_cma: { x: 87.5, y: 51.0, label: 'Room 106 • Valuation & CMA Lab', defaultState: 'idle' },

  desk_intake: { x: 12.5, y: 85.0, label: 'Lobby • Front Reception Counter', defaultState: 'idle' },
  kitchen_cafe: { x: 38.5, y: 85.0, label: 'Café & Kitchen • Espresso Bar', defaultState: 'coffee' },
  watercooler: { x: 52.0, y: 85.0, label: 'Café Breakroom • Watercooler Nook', defaultState: 'chatting' },
  lounge_sofa: { x: 79.0, y: 85.0, label: 'Leisure Lounge • Velvet Sofa', defaultState: 'relaxing' },
};

// Subtle offsets when multiple colleagues occupy the same group room
const GROUP_OFFSETS = {
  manager: { x: -3.5, y: -0.5 },
  it: { x: -1.2, y: 0.5 },
  auditor: { x: 1.2, y: -0.5 },
  intake: { x: 3.5, y: 0.5 },
  finance: { x: -2.2, y: 1.5 },
  marketing: { x: 0.0, y: 1.5 },
  cma: { x: 2.2, y: 1.5 },
};

/**
 * Calculates continuous hallway waypoints from origin zone to destination zone
 */
function computeWaypoints(fromZone, toZone) {
  if (fromZone === toZone) return [];
  const from = FLOOR_ZONES[fromZone];
  const to = FLOOR_ZONES[toZone];
  if (!from || !to) return [];

  const points = [];

  // Determine starting hallway
  let fromHallwayY = 33.2;
  if (from.y < 32) {
    // Step out of Row 1 into North Hallway
    points.push({ x: from.x, y: 31.0 });
    points.push({ x: from.x, y: 33.2 });
    fromHallwayY = 33.2;
  } else if (from.y > 67) {
    // Step out of Row 3 into South Hallway
    points.push({ x: from.x, y: 71.0 });
    points.push({ x: from.x, y: 68.7 });
    fromHallwayY = 68.7;
  } else {
    // In Row 2
    if (to.y < 32) {
      points.push({ x: from.x, y: 35.5 });
      points.push({ x: from.x, y: 33.2 });
      fromHallwayY = 33.2;
    } else {
      points.push({ x: from.x, y: 66.5 });
      points.push({ x: from.x, y: 68.7 });
      fromHallwayY = 68.7;
    }
  }

  // Determine target hallway
  const targetHallwayY = to.y < 32 ? 33.2 : to.y > 67 ? 68.7 : (fromHallwayY === 33.2 ? 33.2 : 68.7);

  // If transition between North Promenade and South Commons is needed
  if (fromHallwayY !== targetHallwayY) {
    const midX = (from.x + to.x) / 2;
    let connectorX = 58.3; // central connector
    if (midX <= 38) connectorX = 24.5; // west connector
    else if (midX >= 68) connectorX = 75.0; // east connector

    points.push({ x: connectorX, y: fromHallwayY });
    points.push({ x: connectorX, y: targetHallwayY });
  }

  // Stride horizontally down target hallway towards destination door
  points.push({ x: to.x, y: targetHallwayY });

  // Step through room doorway
  if (to.y < 32) {
    points.push({ x: to.x, y: 31.0 });
  } else if (to.y > 67) {
    points.push({ x: to.x, y: 71.0 });
  } else {
    if (targetHallwayY === 33.2) {
      points.push({ x: to.x, y: 35.5 });
    } else {
      points.push({ x: to.x, y: 66.5 });
    }
  }

  // Arrive at destination anchor
  points.push({ x: to.x, y: to.y });

  return points;
}

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
  const [zoomLevel, setZoomLevel] = useState(1);

  // Map agent ID to live server state from parent
  const agentStateMap = useMemo(() => {
    const map = {};
    agents.forEach((a) => {
      map[a.id] = a;
    });
    return map;
  }, [agents]);

  // Unified dynamic position state for all 7 employees
  const [agentStates, setAgentStates] = useState({
    manager: {
      zone: 'desk_manager',
      pos: { x: FLOOR_ZONES.desk_manager.x, y: FLOOR_ZONES.desk_manager.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
    it: {
      zone: 'desk_it',
      pos: { x: FLOOR_ZONES.desk_it.x, y: FLOOR_ZONES.desk_it.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
    auditor: {
      zone: 'desk_auditor',
      pos: { x: FLOOR_ZONES.desk_auditor.x, y: FLOOR_ZONES.desk_auditor.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
    intake: {
      zone: 'desk_intake',
      pos: { x: FLOOR_ZONES.desk_intake.x, y: FLOOR_ZONES.desk_intake.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
    finance: {
      zone: 'desk_finance',
      pos: { x: FLOOR_ZONES.desk_finance.x, y: FLOOR_ZONES.desk_finance.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
    marketing: {
      zone: 'desk_marketing',
      pos: { x: FLOOR_ZONES.desk_marketing.x, y: FLOOR_ZONES.desk_marketing.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
    cma: {
      zone: 'desk_cma',
      pos: { x: FLOOR_ZONES.desk_cma.x, y: FLOOR_ZONES.desk_cma.y },
      facing: 'right',
      state: 'idle',
      isWalking: false,
      statusText: null,
    },
  });

  const timeoutsRef = useRef({});

  const triggerEspresso = useCallback(() => {
    setSteamActive(true);
    setTimeout(() => setSteamActive(false), 6000);
  }, []);

  const triggerWatercooler = useCallback(() => {
    setWaterBubbles(true);
    setTimeout(() => setWaterBubbles(false), 5000);
  }, []);

  // Dispatch an agent to walk step-by-step across corridors
  const walkAgentTo = useCallback((agentId, targetZone) => {
    // Clear any pending transition for this agent
    if (timeoutsRef.current[agentId]) {
      clearTimeout(timeoutsRef.current[agentId]);
      delete timeoutsRef.current[agentId];
    }

    setAgentStates((prev) => {
      const cur = prev[agentId];
      if (!cur || cur.zone === targetZone) return prev;

      const waypoints = computeWaypoints(cur.zone, targetZone);
      if (!waypoints.length) return prev;

      const targetInfo = FLOOR_ZONES[targetZone] || FLOOR_ZONES.desk_manager;
      const targetLabel = targetInfo.label.split('•')[0].trim();
      const statusText = `Walking to ${targetLabel}...`;

      let stepIndex = 0;

      const runStep = () => {
        if (stepIndex >= waypoints.length) {
          // Arrived at destination
          setAgentStates((s) => {
            const currentAg = s[agentId];
            if (!currentAg) return s;
            const isGroupZone = ['boardroom', 'kitchen_cafe', 'watercooler', 'lounge_sofa'].includes(targetZone);
            const offset = isGroupZone ? (GROUP_OFFSETS[agentId] || { x: 0, y: 0 }) : { x: 0, y: 0 };
            return {
              ...s,
              [agentId]: {
                ...currentAg,
                zone: targetZone,
                pos: {
                  x: waypoints[waypoints.length - 1].x + offset.x,
                  y: waypoints[waypoints.length - 1].y + offset.y,
                },
                isWalking: false,
                state: targetInfo.defaultState,
                statusText: null,
              },
            };
          });

          if (targetZone === 'kitchen_cafe') triggerEspresso();
          if (targetZone === 'watercooler') triggerWatercooler();
          return;
        }

        const nextPt = waypoints[stepIndex];
        stepIndex++;

        setAgentStates((s) => {
          const currentAg = s[agentId];
          if (!currentAg) return s;
          const newFacing =
            nextPt.x < currentAg.pos.x ? 'left' : nextPt.x > currentAg.pos.x ? 'right' : currentAg.facing;

          return {
            ...s,
            [agentId]: {
              ...currentAg,
              pos: nextPt,
              facing: newFacing,
              isWalking: true,
              state: 'walking',
              statusText,
            },
          };
        });

        timeoutsRef.current[agentId] = setTimeout(runStep, 800);
      };

      // Start first step after quick frame
      timeoutsRef.current[agentId] = setTimeout(runStep, 40);

      return {
        ...prev,
        [agentId]: {
          ...cur,
          isWalking: true,
          state: 'walking',
          statusText,
        },
      };
    });
  }, [triggerEspresso, triggerWatercooler]);

  // Periodic autonomous life cycle: pick one idle employee to stroll
  useEffect(() => {
    const cycleTimer = setInterval(() => {
      // Find agents not currently walking and not busy with a real active live request
      setAgentStates((prev) => {
        const available = Object.keys(prev).filter((id) => {
          const ag = prev[id];
          const isLiveBusy = agentStateMap[id]?.status === 'active';
          return !ag.isWalking && !isLiveBusy;
        });

        if (!available.length) return prev;

        // Choose a random available colleague
        const chosenId = available[Math.floor(Math.random() * available.length)];
        const currentZone = prev[chosenId].zone;

        let targetZone = `desk_${chosenId}`;
        if (currentZone.startsWith('desk_')) {
          // If at desk, 45% Kitchen, 25% Lounge, 20% Boardroom, 10% Watercooler
          const roll = Math.random();
          if (roll < 0.45) targetZone = 'kitchen_cafe';
          else if (roll < 0.70) targetZone = 'lounge_sofa';
          else if (roll < 0.90) targetZone = 'boardroom';
          else targetZone = 'watercooler';
        } else {
          // If already away, return to desk
          targetZone = `desk_${chosenId}`;
        }

        // Trigger the walk
        setTimeout(() => walkAgentTo(chosenId, targetZone), 100);
        return prev;
      });
    }, 22000);

    return () => clearInterval(cycleTimer);
  }, [agentStateMap, walkAgentTo]);

  // If a real task becomes active, immediately walk that agent back to their desk
  useEffect(() => {
    agents.forEach((ag) => {
      if (ag.status === 'active') {
        const homeDesk = `desk_${ag.id}`;
        const currentZone = agentStates[ag.id]?.zone;
        if (currentZone && currentZone !== homeDesk && !agentStates[ag.id]?.isWalking) {
          walkAgentTo(ag.id, homeDesk);
        }
      }
    });
  }, [agents, agentStates, walkAgentTo]);

  const handleAgentClick = (agentId) => {
    setActiveAgentId(agentId);
    const ag = agentStateMap[agentId];
    if (onSelectAgent && ag) {
      onSelectAgent(ag);
    }
  };

  // Group quick commands
  const gatherAllInBoardroom = () => {
    Object.keys(agentStates).forEach((id, idx) => {
      setTimeout(() => walkAgentTo(id, 'boardroom'), idx * 300);
    });
  };

  const sendAllToDesks = () => {
    Object.keys(agentStates).forEach((id, idx) => {
      setTimeout(() => walkAgentTo(id, `desk_${id}`), idx * 250);
    });
  };

  return (
    <div className="flex flex-col gap-4 select-none">
      {/* Map Control Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 text-xs shadow-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-serif font-bold text-neutral-800 dark:text-neutral-200">
            <Compass className="w-4 h-4 text-indigo-500 animate-spin-slow" />
            <span>Bellevue HQ • Floor 4 Blueprint</span>
          </div>
          <span className="hidden sm:inline text-neutral-400">•</span>
          <span className="hidden sm:inline text-neutral-500 text-[11px]">
            Autonomous Room-to-Room Walking & Live Corridor Navigation
          </span>
        </div>

        {/* Action Controls & Zoom */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Quick Group Walk Controls */}
          <button
            type="button"
            onClick={gatherAllInBoardroom}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/70 border border-indigo-200 dark:border-indigo-800 text-[11px] font-bold text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 transition-colors"
            title="Command all agents to walk to Olympic Boardroom for strategy"
          >
            <Users className="w-3.5 h-3.5 text-indigo-500" />
            <span>Team to Boardroom</span>
          </button>

          <button
            type="button"
            onClick={sendAllToDesks}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-neutral-100 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 text-[11px] font-bold text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 transition-colors"
            title="Command all agents to return to their personal workstation desks"
          >
            <RotateCcw className="w-3.5 h-3.5 text-neutral-500" />
            <span>All to Desks</span>
          </button>

          {/* Zoom controls */}
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
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-xs font-bold transition-all ${
              steamActive
                ? 'bg-amber-500 text-white border-amber-600 shadow-xs'
                : 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800 hover:bg-amber-100'
            }`}
          >
            <Coffee className="w-3.5 h-3.5" />
            <span>{steamActive ? 'Brewing...' : 'Espresso'}</span>
          </button>
        </div>
      </div>

      {/* Main Architectural Floor Canvas with Room Suites & Hallway Corridors */}
      <div className="relative rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden p-4 sm:p-6 transition-all">
        <div
          className="overflow-x-auto pb-4 transition-transform origin-top-left"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <div className="min-w-[1020px] max-w-[1200px] mx-auto relative rounded-xl border-4 border-neutral-800/80 dark:border-neutral-700/80 bg-[#FAF9F5] dark:bg-[#16171A] p-4 shadow-inner">
            
            {/* North Compass Rose */}
            <div className="absolute top-2 right-4 flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-neutral-400 dark:text-neutral-600 pointer-events-none">
              <span>N</span>
              <div className="w-2 h-2 border-t-2 border-r-2 border-indigo-400 rotate-45" />
              <span>Bellevue HQ</span>
            </div>

            {/* ========================================================= */}
            {/* TOP ROW: SUITES 101, 102, 104, 105                        */}
            {/* ========================================================= */}
            <div className="grid grid-cols-12 gap-3">
              
              {/* SUITE 101: Corner Executive Suite (Marcus Vance) */}
              <div
                onClick={() => setSelectedRoom('Room 101: Executive Suite')}
                className="col-span-3 h-64 rounded-xl border-2 border-amber-800/40 dark:border-amber-600/30 bg-[#F4EFE6]/70 dark:bg-[#1F1D1A]/70 p-3 relative flex flex-col justify-between group hover:border-indigo-400 transition-colors shadow-xs"
              >
                <div className="flex items-center justify-between border-b border-amber-900/10 dark:border-amber-500/20 pb-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-900 dark:text-amber-400">
                    Suite 101 • Executive
                  </span>
                  <span className="text-[9px] text-neutral-400 font-mono">Corner</span>
                </div>

                <div className="absolute top-0 left-10 right-10 h-1.5 bg-sky-200 dark:bg-sky-900/80 rounded-b shadow-xs flex items-center justify-center">
                  <span className="text-[7px] text-sky-700 dark:text-sky-300 uppercase">Skyline View</span>
                </div>

                {/* Desk Furniture */}
                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  <div className="w-36 h-20 rounded-lg bg-[#5C4033] dark:bg-[#3D2817] border-2 border-[#3D2817] dark:border-[#24170D] shadow-md relative flex flex-col items-center justify-center p-2">
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

                  {/* Leather Guest Chairs */}
                  <div className="flex justify-between w-32 mt-2">
                    <div className="w-8 h-8 rounded-full bg-[#3E2723] border border-amber-950 shadow-xs" />
                    <div className="w-8 h-8 rounded-full bg-[#3E2723] border border-amber-950 shadow-xs" />
                  </div>
                </div>

                {/* Door Opening to Hallway */}
                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-amber-700 dark:border-amber-500" title="Door 101" />

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
                    {[1, 2, 3, 4, 5, 6].map((unit) => (
                      <div key={unit} className="flex items-center justify-between py-0.5 px-1 bg-neutral-800 rounded-xs">
                        <span className="w-1.5 h-1 bg-neutral-600 rounded-xs" />
                        <div className="flex items-center gap-1">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              unit === 2 ? 'bg-amber-400' : 'bg-emerald-400'
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
                      <div className="w-14 h-2 bg-neutral-700 rounded-xs mt-1 border border-neutral-600" />
                    </div>
                  </div>
                </div>

                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-emerald-700 dark:border-emerald-500" title="Door 102" />

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
                  <span className="text-[9px] text-teal-600 dark:text-teal-400 font-mono">GL Budget</span>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  <div className="w-34 h-20 rounded-lg bg-[#2E4A47] border-2 border-[#1B3230] shadow-md relative flex flex-col items-center justify-center p-2">
                    <div className="absolute top-1 left-2 flex items-center gap-1">
                      <div className="w-3 h-2 rounded-t-sm bg-emerald-500 border border-emerald-300 shadow-xs" title="Banker's Lamp" />
                      <div className="w-2 h-2 rounded-xs bg-amber-100" title="Calculator" />
                    </div>
                    <div className="w-12 h-7 rounded bg-neutral-900 border border-teal-500 p-0.5">
                      <div className="w-full h-full bg-teal-950 text-[6px] font-mono text-teal-300 flex items-center justify-center">
                        GL: $ OK
                      </div>
                    </div>
                    <div className="absolute bottom-1 right-2 flex gap-0.5">
                      <div className="w-1 h-3 bg-red-700 rounded-xs" />
                      <div className="w-1 h-3 bg-blue-700 rounded-xs" />
                      <div className="w-1 h-3 bg-emerald-700 rounded-xs" />
                    </div>
                  </div>
                </div>

                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-teal-700 dark:border-teal-500" title="Door 104" />

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

                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  <div className="w-34 h-20 rounded-lg bg-[#E2D8C6] dark:bg-[#382B29] border-2 border-[#C9BCA8] dark:border-[#523F3C] shadow-md relative flex flex-col items-center justify-center p-2">
                    <div className="absolute top-1 left-2 flex gap-0.5">
                      <span className="w-1.5 h-2 bg-rose-500 rounded-xs" />
                      <span className="w-1.5 h-2 bg-amber-500 rounded-xs" />
                      <span className="w-1.5 h-2 bg-indigo-500 rounded-xs" />
                    </div>
                    <div className="w-11 h-8 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center">
                      <span className="text-[8px] text-rose-300 font-bold">🎨 Art</span>
                    </div>
                  </div>
                </div>

                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-rose-700 dark:border-rose-500" title="Door 105" />

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Maya Reyes • Creative Director
                </div>
              </div>

            </div>

            {/* ========================================================= */}
            {/* NORTH PROMENADE HALLWAY CORRIDOR                          */}
            {/* ========================================================= */}
            <div className="h-10 my-2 rounded-xl bg-gradient-to-r from-neutral-200/70 via-neutral-100/60 to-neutral-200/70 dark:from-neutral-900/60 dark:via-neutral-800/50 dark:to-neutral-900/60 border border-neutral-300 dark:border-neutral-700/70 flex items-center justify-between px-6 shadow-inner select-none">
              <div className="flex items-center gap-3 text-[10px] font-mono font-medium text-neutral-500 dark:text-neutral-400">
                <span className="flex items-center gap-1">◀ Suite 101 (Executive)</span>
                <span className="text-neutral-300 dark:text-neutral-700">|</span>
                <span>DevOps Lab 102</span>
                <span className="text-neutral-300 dark:text-neutral-700">|</span>
                <span>🌿 North Planter</span>
              </div>
              <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-widest text-indigo-500 dark:text-indigo-400 font-bold bg-white/70 dark:bg-charcoal/70 px-2.5 py-0.5 rounded-full border border-indigo-200 dark:border-indigo-800 shadow-xs">
                North Promenade
              </div>
              <div className="flex items-center gap-3 text-[10px] font-mono font-medium text-neutral-500 dark:text-neutral-400">
                <span>Suites 104 & 105 (Finance & Creative) ▶</span>
              </div>
            </div>

            {/* ========================================================= */}
            {/* MIDDLE ROW: QA, OLYMPIC BOARDROOM, PODS, CMA LAB           */}
            {/* ========================================================= */}
            <div className="grid grid-cols-12 gap-3">
              
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
                  <div className="w-34 h-20 rounded-lg bg-neutral-200 dark:bg-neutral-800 border-2 border-neutral-300 dark:border-neutral-700 shadow-md relative flex flex-col items-center justify-center p-2">
                    <div className="absolute top-1 left-2 flex items-center gap-1">
                      <div className="w-2.5 h-2.5 rounded-xs bg-rose-600 text-[6px] text-white flex items-center justify-center" title="Approved Stamp">
                        ✓
                      </div>
                      <div className="w-2.5 h-3.5 bg-amber-200 rounded-xs border border-amber-400" title="Audit Checklist" />
                    </div>
                    <div className="w-12 h-7 rounded bg-neutral-900 border border-amber-500 p-0.5">
                      <div className="w-full h-full bg-neutral-950 text-[6px] font-mono text-emerald-400 flex items-center justify-center">
                        TESTS: PASS
                      </div>
                    </div>
                  </div>
                </div>

                {/* Doors North & South */}
                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-amber-700 dark:border-amber-500" title="Door 103 North" />
                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-amber-700 dark:border-amber-500" title="Door 103 South" />

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

                <div className="flex-1 flex flex-col items-center justify-center relative mt-1">
                  <div className="w-36 h-4 bg-neutral-900 border border-indigo-400 rounded-b-xs text-[7px] font-mono text-cyan-300 flex items-center justify-center mb-1 shadow-xs">
                    Casa-Poki Roadmap & Strategy
                  </div>

                  <div className="w-48 h-20 rounded-full bg-[#4A2511] border-2 border-[#2E1508] shadow-lg relative flex items-center justify-center">
                    <div className="w-4 h-4 rounded-full bg-neutral-800 border border-neutral-600 flex items-center justify-center text-[7px] text-neutral-300">
                      🎙️
                    </div>
                  </div>

                  {/* Swivel Chairs */}
                  <div className="flex justify-between w-44 mt-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="w-5 h-5 rounded-full bg-neutral-800 border border-neutral-600 shadow-xs" />
                    ))}
                  </div>
                </div>

                {/* Double doors */}
                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-10 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-indigo-700 dark:border-indigo-500" title="Boardroom North Door" />
                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-10 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-indigo-700 dark:border-indigo-500" title="Boardroom South Door" />

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center">
                  Glass Whiteboard • Interactive Strategy Sessions
                </div>
              </div>

              {/* BREAKOUT FOCUS PODS */}
              <div className="col-span-2 h-64 flex flex-col gap-2">
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

                <div className="flex-1 flex flex-col items-center justify-center relative mt-2">
                  <div className="w-34 h-20 rounded-lg bg-[#2E3B55] border-2 border-[#1E293B] shadow-md relative flex flex-col items-center justify-center p-2">
                    <div className="w-20 h-10 bg-sky-950 rounded-xs border border-sky-400 flex items-center justify-center relative">
                      <span className="text-[6px] text-sky-200 font-mono">King County</span>
                      <span className="absolute top-1 left-2 w-1.5 h-1.5 rounded-full bg-red-500" title="Bellevue" />
                      <span className="absolute bottom-2 right-3 w-1.5 h-1.5 rounded-full bg-amber-400" title="Renton" />
                    </div>
                  </div>
                </div>

                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-purple-700 dark:border-purple-500" title="Door 106 North" />
                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-purple-700 dark:border-purple-500" title="Door 106 South" />

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center font-serif">
                  Carter Hayes • CMA & Valuation Specialist
                </div>
              </div>

            </div>

            {/* ========================================================= */}
            {/* SOUTH COMMONS HALLWAY CORRIDOR                            */}
            {/* ========================================================= */}
            <div className="h-10 my-2 rounded-xl bg-gradient-to-r from-neutral-200/70 via-neutral-100/60 to-neutral-200/70 dark:from-neutral-900/60 dark:via-neutral-800/50 dark:to-neutral-900/60 border border-neutral-300 dark:border-neutral-700/70 flex items-center justify-between px-6 shadow-inner select-none">
              <div className="flex items-center gap-3 text-[10px] font-mono font-medium text-neutral-500 dark:text-neutral-400">
                <span className="flex items-center gap-1">◀ Front Lobby & Reception</span>
                <span className="text-neutral-300 dark:text-neutral-700">|</span>
                <span>📌 Community Notice Board</span>
              </div>
              <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-widest text-emerald-500 dark:text-emerald-400 font-bold bg-white/70 dark:bg-charcoal/70 px-2.5 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800 shadow-xs">
                Central Commons
              </div>
              <div className="flex items-center gap-3 text-[10px] font-mono font-medium text-neutral-500 dark:text-neutral-400">
                <span>☕ Café & Wellness Lounge ▶</span>
              </div>
            </div>

            {/* ========================================================= */}
            {/* BOTTOM ROW: RECEPTION LOBBY, KITCHEN CAFÉ, LEISURE LOUNGE */}
            {/* ========================================================= */}
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

                <div className="flex-1 flex flex-col items-center justify-center relative mt-1">
                  <div className="w-36 h-18 rounded-t-2xl rounded-b-lg bg-[#E0E7FF] dark:bg-[#1E293B] border-2 border-blue-300 dark:border-blue-700 shadow-md relative flex flex-col items-center justify-center p-2">
                    <div className="absolute top-1 right-2 flex items-center gap-1">
                      <div className="w-4 h-6 rounded-xs bg-black border border-white flex items-center justify-center text-[5px] text-cyan-300 font-mono" title="Open House Check-in iPad">
                        iPad
                      </div>
                    </div>
                    <div className="absolute bottom-1 left-2 flex gap-0.5">
                      <div className="w-3 h-2 bg-neutral-700 rounded-xs" title="Telephone" />
                      <div className="w-2 h-2 bg-amber-200 rounded-xs" title="Mail" />
                    </div>
                  </div>
                </div>

                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-blue-700 dark:border-blue-500" title="Lobby Door" />

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

                <div className="flex-1 flex items-center justify-between px-2 mt-2 relative">
                  {/* Left: Refrigerator & Snack Counter */}
                  <div className="flex flex-col items-center">
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
                      <div className="w-10 h-7 rounded bg-neutral-900 border border-amber-500 relative flex items-center justify-center">
                        <div className="w-2 h-1 bg-amber-400 rounded-xs" />
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
                      {waterBubbles && <div className="text-[7px] animate-bounce">🫧</div>}
                    </div>
                    <div className="w-8 h-10 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-b flex items-center justify-center">
                      <span className="text-[6px] text-sky-500">H2O</span>
                    </div>
                  </div>
                </div>

                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-amber-700 dark:border-amber-500" title="Kitchen Door" />

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

                <div className="flex-1 flex items-center justify-between px-4 mt-1 relative">
                  <div className="flex flex-col items-center" title="Monstera Deliciosa">
                    <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center text-sm shadow-xs">
                      🪴
                    </div>
                    <span className="text-[7px] text-neutral-400 mt-0.5">Monstera</span>
                  </div>

                  <div className="flex flex-col items-center relative">
                    <div className="w-56 h-18 rounded-xl bg-[#2D4A3E] border-2 border-[#1E332A] shadow-md flex flex-col items-center justify-center relative p-1">
                      <div className="w-28 h-6 rounded bg-neutral-200/90 dark:bg-neutral-800/90 border border-neutral-300 dark:border-neutral-700 flex items-center justify-center gap-2">
                        <span className="text-[6px] font-mono text-neutral-500">Architectural Digest</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-center">
                    <div className="w-4 h-4 rounded-full bg-amber-300 border border-amber-500 shadow-sm" title="Warm Ambient Floor Lamp" />
                    <div className="w-0.5 h-14 bg-neutral-400" />
                  </div>
                </div>

                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-8 h-1.5 bg-[#FAF9F5] dark:bg-[#16171A] border-l border-r border-emerald-700 dark:border-emerald-500" title="Lounge Door" />

                <div className="text-[9px] text-neutral-500 dark:text-neutral-400 text-center">
                  Acoustic Rug • Velvet Lounge Sofa • Real Estate Periodicals
                </div>
              </div>

            </div>

            {/* ========================================================= */}
            {/* ABSOLUTE AGENT WALKING LAYER                              */}
            {/* Renders all 7 employees with continuous smooth navigation */}
            {/* ========================================================= */}
            <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden">
              {Object.keys(agentStates).map((id) => {
                const ag = agentStates[id];
                const liveStatus = agentStateMap[id]?.status;
                const effectiveState = liveStatus === 'active' && !ag.isWalking ? 'active' : ag.state;

                return (
                  <div
                    key={id}
                    style={{
                      position: 'absolute',
                      left: `${ag.pos.x}%`,
                      top: `${ag.pos.y}%`,
                      transform: 'translate(-50%, -50%)',
                      transition: ag.isWalking ? 'left 0.8s linear, top 0.8s linear' : 'none',
                      pointerEvents: 'auto',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAgentClick(id);
                    }}
                    className="cursor-pointer group flex flex-col items-center"
                  >
                    {/* Floating Status Pill while Walking */}
                    {ag.isWalking && (
                      <div className="mb-1 px-2.5 py-0.5 rounded-full bg-indigo-600 text-white text-[9px] font-bold shadow-md whitespace-nowrap animate-bounce flex items-center gap-1 border border-indigo-400">
                        <Footprints className="w-2.5 h-2.5 text-indigo-200" />
                        <span>{ag.statusText || 'Walking...'}</span>
                      </div>
                    )}

                    {/* Coffee badge */}
                    {!ag.isWalking && effectiveState === 'coffee' && (
                      <div className="mb-0.5 px-2 py-0.2 rounded-full bg-amber-500 text-white text-[8px] font-bold shadow-xs whitespace-nowrap flex items-center gap-1">
                        <span>Espresso ☕</span>
                      </div>
                    )}

                    {/* Relaxing badge */}
                    {!ag.isWalking && effectiveState === 'relaxing' && (
                      <div className="mb-0.5 px-2 py-0.2 rounded-full bg-emerald-600 text-white text-[8px] font-bold shadow-xs whitespace-nowrap flex items-center gap-1">
                        <span>Lounge Break 🛋️</span>
                      </div>
                    )}

                    {/* Chatting in Boardroom badge */}
                    {!ag.isWalking && ag.zone === 'boardroom' && (
                      <div className="mb-0.5 px-2 py-0.2 rounded-full bg-indigo-600 text-white text-[8px] font-bold shadow-xs whitespace-nowrap flex items-center gap-1">
                        <span>Strategy Session 📋</span>
                      </div>
                    )}

                    {/* Avatar Character Sprite */}
                    <AvatarCharacter
                      agentId={id}
                      state={effectiveState}
                      facing={ag.facing}
                      size={ag.isWalking ? 50 : 54}
                      className="transition-transform group-hover:scale-110 drop-shadow-md"
                    />
                  </div>
                );
              })}
            </div>

          </div>
        </div>

        {/* Selected Room / Agent Interactive Flyout Drawer */}
        {(selectedRoom || activeAgentId) && (
          <div className="mt-4 p-4 rounded-xl bg-indigo-50/90 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all">
            
            <div className="flex items-center gap-3">
              {activeAgentId ? (
                <div className="w-12 h-12 flex-shrink-0">
                  <AvatarCharacter
                    agentId={activeAgentId}
                    state={agentStates[activeAgentId]?.state || 'idle'}
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
                      <strong>Location:</strong>{' '}
                      {FLOOR_ZONES[agentStates[activeAgentId]?.zone]?.label || 'On Floor'} •{' '}
                      <em>{agentStates[activeAgentId]?.isWalking ? 'Walking in corridor' : 'At station'}</em>
                    </>
                  ) : (
                    'Click any desk, colleague, or room to inspect activities and order walks.'
                  )}
                </p>
              </div>
            </div>

            {/* Quick Walk & Action Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              {activeAgentId && (
                <>
                  <button
                    type="button"
                    onClick={() => walkAgentTo(activeAgentId, 'kitchen_cafe')}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-amber-100 hover:bg-amber-200 text-amber-800 dark:bg-amber-950 dark:text-amber-300 transition-colors flex items-center gap-1 shadow-xs"
                    title="Send this colleague to the kitchen for coffee"
                  >
                    <Coffee className="w-3.5 h-3.5" />
                    <span>Walk to Kitchen</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => walkAgentTo(activeAgentId, 'lounge_sofa')}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-100 hover:bg-emerald-200 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 transition-colors flex items-center gap-1 shadow-xs"
                    title="Send this colleague to the lounge sofa"
                  >
                    <span>🛋️ Walk to Lounge</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => walkAgentTo(activeAgentId, 'boardroom')}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-indigo-100 hover:bg-indigo-200 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300 transition-colors flex items-center gap-1 shadow-xs"
                    title="Send this colleague to the Olympic Boardroom"
                  >
                    <span>📋 Walk to Boardroom</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => walkAgentTo(activeAgentId, `desk_${activeAgentId}`)}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-neutral-200 hover:bg-neutral-300 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200 transition-colors flex items-center gap-1 shadow-xs"
                    title="Call colleague back to their desk"
                  >
                    <span>💻 Return to Desk</span>
                  </button>

                  {onOpenChat && (
                    <button
                      type="button"
                      onClick={() => onOpenChat(activeAgentId)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors flex items-center gap-1.5 shadow-xs"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>Chat</span>
                    </button>
                  )}
                </>
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
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" /> Walking in Corridors
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Coffee Break in Kitchen
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> Relaxing in Lounge
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500" /> Olympic Boardroom
          </span>
        </div>
        <div className="flex items-center gap-1 text-neutral-400">
          <span>Tip: Click on any colleague to dispatch them to another room on demand!</span>
        </div>
      </div>
    </div>
  );
}
