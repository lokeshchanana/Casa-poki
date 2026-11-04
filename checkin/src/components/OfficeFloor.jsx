import React, { useState, useEffect, useCallback } from 'react';
import OfficeFloorMap from './OfficeFloorMap';
import AvatarCharacter from './AvatarCharacter';
import {
  Users,
  Activity,
  Server,
  ShieldCheck,
  RefreshCw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  Terminal,
  Layers,
  ArrowRight,
  ExternalLink,
  Cpu,
  Database,
  Coffee,
  MessageSquare,
  Sparkles,
  Search,
  Eye
} from 'lucide-react';

export default function OfficeFloor({ onOpenChat }) {
  const [floorState, setFloorState] = useState(null);
  const [containers, setContainers] = useState([]);
  const [monitors, setMonitors] = useState([]);
  const [selectedFlow, setSelectedFlow] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [activeView, setActiveView] = useState('floor'); // 'floor' | 'inspector' | 'telemetry'
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [healingContainer, setHealingContainer] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');

  // Fetch all floor and telemetry data
  const refreshData = useCallback(async () => {
    try {
      const [floorRes, contRes, monRes] = await Promise.all([
        fetch('/api/manager/office/floor-state').then(r => r.json()).catch(() => null),
        fetch('/api/manager/office/containers').then(r => r.json()).catch(() => ({ containers: [] })),
        fetch('/api/manager/office/monitors').then(r => r.json()).catch(() => ({ monitors: [] })),
      ]);

      if (floorRes) {
        setFloorState(floorRes);
        if (!selectedFlow && floorRes.recent_flows?.length > 0) {
          setSelectedFlow(floorRes.recent_flows[0]);
        }
      }
      if (contRes?.containers) setContainers(contRes.containers);
      if (monRes?.monitors) setMonitors(monRes.monitors);
    } catch (err) {
      console.error('Failed to fetch office floor state:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedFlow]);

  useEffect(() => {
    refreshData();
    if (!autoRefresh) return;
    const interval = setInterval(refreshData, 6000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshData]);

  const triggerHeal = async (containerName) => {
    if (!confirm(`Trigger emergency restart for '${containerName}'?`)) return;
    setHealingContainer(containerName);
    try {
      const res = await fetch('/api/manager/office/heal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ container_name: containerName }),
      });
      const data = await res.json();
      if (!res.ok) alert(`Healing failed: ${data.detail || data.error}`);
      else alert(`Healing successful: Container '${containerName}' restarted.`);
      refreshData();
    } catch (err) {
      alert(`Healing error: ${err.message}`);
    } finally {
      setHealingContainer(null);
    }
  };

  const agents = floorState?.agents || [];
  const flows = floorState?.recent_flows || [];
  const activeCount = agents.filter(a => a.status === 'active').length;
  const healthyContainers = containers.filter(c => c.state === 'running').length;
  const upMonitors = monitors.filter(m => m.status === 'UP').length;

  const filteredFlows = flows.filter(f => {
    if (!searchFilter) return true;
    const q = searchFilter.toLowerCase();
    return (
      f.title?.toLowerCase().includes(q) ||
      f.source?.toLowerCase().includes(q) ||
      f.agents_involved?.some(a => a.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex-1 flex flex-col bg-ivory dark:bg-charcoal min-h-screen text-neutral-900 dark:text-neutral-100 transition-colors">
      
      {/* Top Banner & Control Bar */}
      <div className="bg-white/80 dark:bg-charcoal-dark/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 px-4 sm:px-8 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                <Users className="w-5 h-5" />
              </span>
              <h2 className="text-xl font-serif font-bold text-neutral-900 dark:text-white">
                Virtual Office Floor
              </h2>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live Agent Operations
              </span>
            </div>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
              Autonomous workforce floor map, real-time agent activities, and end-to-end request flow tracing.
            </p>
          </div>

          {/* Quick Metrics Bar & Controls */}
          <div className="flex items-center flex-wrap gap-2 sm:gap-4">
            
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-xl bg-neutral-100 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="text-neutral-400">Agents:</span>
                <span className="font-bold text-neutral-900 dark:text-neutral-100">{agents.length}</span>
                {activeCount > 0 ? (
                  <span className="text-[10px] text-amber-500 font-semibold">({activeCount} busy)</span>
                ) : (
                  <span className="text-[10px] text-neutral-400">(All Idle)</span>
                )}
              </div>
              <div className="w-px h-3.5 bg-neutral-300 dark:bg-neutral-700" />
              <div className="flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-emerald-500" />
                <span className="font-bold text-emerald-600 dark:text-emerald-400">{healthyContainers}/{containers.length || 17} Up</span>
              </div>
              <div className="w-px h-3.5 bg-neutral-300 dark:bg-neutral-700" />
              <div className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-cyan-500" />
                <span className="font-bold text-cyan-600 dark:text-cyan-400">{upMonitors}/{monitors.length || 17} Kuma</span>
              </div>
            </div>

            {/* View Switcher Tabs */}
            <div className="flex items-center p-1 bg-neutral-100 dark:bg-charcoal rounded-xl border border-neutral-200 dark:border-neutral-800 text-xs">
              <button
                type="button"
                onClick={() => setActiveView('floor')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all ${
                  activeView === 'floor'
                    ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                    : 'text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Layers className="w-3.5 h-3.5 text-indigo-500" />
                <span>Office Floor</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveView('inspector')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all ${
                  activeView === 'inspector'
                    ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                    : 'text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <ArrowRight className="w-3.5 h-3.5 text-cyan-500" />
                <span>Flow Inspector</span>
                {flows.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                    {flows.length}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveView('telemetry')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all ${
                  activeView === 'telemetry'
                    ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                    : 'text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Server className="w-3.5 h-3.5 text-emerald-500" />
                <span>Guardian Telemetry</span>
              </button>
            </div>

            {/* Refresh Controls */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={refreshData}
                disabled={loading}
                className="p-2 rounded-lg bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                title="Refresh floor state"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-neutral-600 dark:text-neutral-400 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <button
                type="button"
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                  autoRefresh
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800'
                    : 'bg-neutral-100 dark:bg-charcoal text-neutral-500 border-neutral-300 dark:border-neutral-700'
                }`}
                title="Toggle live 6-second auto poll"
              >
                {autoRefresh ? 'Live' : 'Paused'}
              </button>
            </div>

          </div>

        </div>
      </div>

      {/* Main Floor Container */}
      <div className="max-w-7xl mx-auto w-full p-4 sm:p-8 flex-1 flex flex-col gap-6">

        {/* VIEW 1: INTERACTIVE OFFICE FLOOR PLAN */}
        {activeView === 'floor' && (
          <div className="flex flex-col gap-6">
            
            {/* Architectural Interactive Floor Map */}
            <OfficeFloorMap
              agents={agents}
              recentFlows={flows}
              containers={containers}
              monitors={monitors}
              onSelectAgent={(ag) => setSelectedAgent(ag)}
              onOpenChat={onOpenChat}
            />

            {/* Selected Agent Workstation Drawer */}
            {selectedAgent && (
              <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-indigo-200 dark:border-indigo-900 p-6 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <AvatarCharacter agentId={selectedAgent.id} state={selectedAgent.status || 'idle'} size={56} />
                    <div>
                      <h3 className="text-lg font-serif font-bold text-neutral-900 dark:text-white">
                        {selectedAgent.name}
                      </h3>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">
                        {selectedAgent.role} • {selectedAgent.station}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {onOpenChat && (
                      <button
                        type="button"
                        onClick={() => onOpenChat(selectedAgent.id)}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors flex items-center gap-1.5 shadow-xs"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>Chat</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setSelectedAgent(null)}
                      className="text-xs text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200"
                    >
                      Close
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800">
                  <div className="p-3 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Live Status</span>
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mt-1">
                      {selectedAgent.status_text}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Current Task</span>
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mt-1 truncate">
                      {selectedAgent.current_activity}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Domain Responsibility</span>
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mt-1">
                      {selectedAgent.default_activity}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Flow Overview (Bottom of Floor View) */}
            <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4 text-indigo-500" />
                  <h3 className="font-serif font-bold text-neutral-900 dark:text-white text-sm">
                    Recent Multi-Agent Request Traces
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveView('inspector')}
                  className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                >
                  <span>Open Full Flow Inspector</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {flows.length === 0 ? (
                <p className="text-xs text-neutral-500 py-4 text-center">
                  No requests recorded yet. Try sending a message in Manager Chat or an Open House sign-in!
                </p>
              ) : (
                <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
                  {flows.slice(0, 4).map((f) => (
                    <div
                      key={f.flow_id}
                      onClick={() => {
                        setSelectedFlow(f);
                        setActiveView('inspector');
                      }}
                      className="py-3 flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-charcoal/50 px-2 rounded-lg cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className={`w-2 h-2 rounded-full ${f.status === 'completed' ? 'bg-emerald-500' : f.status === 'healed' ? 'bg-amber-500' : 'bg-indigo-500'}`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-neutral-900 dark:text-white">
                              {f.title}
                            </span>
                            <span className="text-[10px] px-2 py-0.2 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400">
                              {f.source}
                            </span>
                          </div>
                          <p className="text-[11px] text-neutral-500 mt-0.5">
                            Agents involved: {f.agents_involved?.join(' → ') || 'Marcus Vance'}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-neutral-400">
                        <span>{f.duration_ms ? `${f.duration_ms}ms` : 'instant'}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* VIEW 2: REQUEST FLOW INSPECTOR */}
        {activeView === 'inspector' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
            
            {/* Left Column: Recent Flows List */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              
              <div className="relative">
                <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter flows by keyword, source, agent..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-4 shadow-sm flex flex-col gap-2 overflow-y-auto max-h-[750px]">
                <div className="text-xs font-bold uppercase tracking-wider text-neutral-400 px-2 py-1">
                  Recorded Functional Flows ({filteredFlows.length})
                </div>

                {filteredFlows.length === 0 ? (
                  <p className="text-xs text-neutral-500 p-4 text-center">
                    No matching flows found.
                  </p>
                ) : (
                  filteredFlows.map((flow) => {
                    const isSelected = selectedFlow?.flow_id === flow.flow_id;
                    return (
                      <div
                        key={flow.flow_id}
                        onClick={() => setSelectedFlow(flow)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-400 dark:border-indigo-600 shadow-sm'
                            : 'bg-neutral-50/60 dark:bg-charcoal/50 hover:bg-neutral-100 dark:hover:bg-charcoal border-neutral-200/80 dark:border-neutral-800'
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-bold text-neutral-900 dark:text-white truncate max-w-[220px]">
                            {flow.title}
                          </span>
                          <span className="text-[10px] text-neutral-400 font-mono">
                            {flow.created_at ? flow.created_at.slice(11, 19) : ''}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 text-[11px] text-neutral-500 dark:text-neutral-400 mb-2">
                          <span className="px-1.5 py-0.2 rounded bg-neutral-200/70 dark:bg-neutral-800 text-[10px]">
                            {flow.source}
                          </span>
                          <span>•</span>
                          <span>{flow.duration_ms || 0}ms</span>
                        </div>

                        {/* Agents Path Pills */}
                        <div className="flex items-center gap-1 flex-wrap">
                          {flow.agents_involved?.map((agent, i) => (
                            <React.Fragment key={agent}>
                              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white dark:bg-charcoal-dark border border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300">
                                {agent}
                              </span>
                              {i < flow.agents_involved.length - 1 && (
                                <ArrowRight className="w-2.5 h-2.5 text-neutral-400" />
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

            </div>

            {/* Right Column: Detailed Flow Visual Pipeline Drawer */}
            <div className="lg:col-span-7">
              {selectedFlow ? (
                <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm flex flex-col gap-6">
                  
                  {/* Flow Header */}
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-neutral-400">
                        {selectedFlow.flow_id}
                      </span>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        selectedFlow.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                          : selectedFlow.status === 'healed'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300'
                          : 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300'
                      }`}>
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {selectedFlow.status.toUpperCase()}
                      </span>
                    </div>

                    <h3 className="text-lg font-serif font-bold text-neutral-900 dark:text-white mt-1">
                      {selectedFlow.title}
                    </h3>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                      Received from: <strong className="text-neutral-800 dark:text-neutral-200">{selectedFlow.source}</strong> • Duration: {selectedFlow.duration_ms}ms
                    </p>
                  </div>

                  {/* Flow Pipeline Visual Nodes */}
                  <div className="flex flex-col gap-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">
                      Functional Pipeline Execution
                    </span>

                    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-neutral-200 dark:before:bg-neutral-800">
                      {selectedFlow.steps?.map((step, idx) => (
                        <div key={idx} className="relative group">
                          {/* Step Marker Dot */}
                          <span className={`absolute -left-[23px] top-1.5 w-4 h-4 rounded-full border-2 border-white dark:border-charcoal-dark ${
                            step.status === 'ok'
                              ? 'bg-emerald-500'
                              : step.status === 'running'
                              ? 'bg-amber-500 animate-pulse'
                              : step.status === 'warning'
                              ? 'bg-amber-400'
                              : 'bg-indigo-500'
                          }`} />

                          <div className="p-3.5 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="font-bold text-neutral-900 dark:text-white">
                                {step.step}
                              </span>
                              <span className="text-[10px] text-neutral-400 font-mono">
                                {step.timestamp ? step.timestamp.slice(11, 19) : ''}
                              </span>
                            </div>

                            <p className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                              Agent: {step.agent}
                            </p>

                            <p className="text-xs text-neutral-600 dark:text-neutral-300 mt-1">
                              {step.action}
                            </p>

                            {step.diagnostics && (
                              <pre className="mt-2 p-2 rounded bg-neutral-900 text-neutral-200 text-[10px] font-mono overflow-x-auto max-h-28">
                                {step.diagnostics}
                              </pre>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Result & Payload Summary */}
                  {selectedFlow.result_summary && (
                    <div className="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400">
                        Result Outcome
                      </span>
                      <p className="text-xs text-emerald-950 dark:text-emerald-200 mt-1">
                        {selectedFlow.result_summary}
                      </p>
                    </div>
                  )}

                  {/* Raw Payload Preview Drawer */}
                  {selectedFlow.payload_preview && (
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-neutral-400 mb-2 block">
                        Payload Snippet
                      </span>
                      <pre className="p-3 rounded-xl bg-neutral-100 dark:bg-charcoal font-mono text-[11px] text-neutral-800 dark:text-neutral-300 overflow-x-auto max-h-48">
                        {typeof selectedFlow.payload_preview === 'object'
                          ? JSON.stringify(selectedFlow.payload_preview, null, 2)
                          : selectedFlow.payload_preview}
                      </pre>
                    </div>
                  )}

                </div>
              ) : (
                <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-12 text-center text-neutral-400">
                  <ArrowRight className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm font-medium">Select a flow from the list to inspect functional execution</p>
                </div>
              )}
            </div>

          </div>
        )}

        {/* VIEW 3: GUARDIAN TELEMETRY & CONTAINERS */}
        {activeView === 'telemetry' && (
          <div className="flex flex-col gap-6">
            
            {/* Header / Intro */}
            <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
                  <Server className="w-6 h-6" />
                </span>
                <div>
                  <h3 className="font-serif font-bold text-lg text-neutral-900 dark:text-white">
                    Ian Torres' Infrastructure Pod
                  </h3>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">
                    Direct Docker Unix socket inspection & Uptime Kuma live heartbeats. Auto-healing triggered on-demand via webhook.
                  </p>
                </div>
              </div>
            </div>

            {/* Containers Grid */}
            <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-serif font-bold text-sm text-neutral-900 dark:text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-emerald-500" />
                  <span>Docker Containers ({containers.length})</span>
                </h4>
                <span className="text-xs text-neutral-400">
                  Protected: real-estate (prod)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {containers.map((c) => {
                  const isUp = c.state === 'running';
                  const isHealing = healingContainer === c.name;

                  return (
                    <div
                      key={c.id || c.name}
                      className="p-3.5 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                          <h5 className="font-bold text-xs text-neutral-900 dark:text-white truncate">
                            {c.name}
                          </h5>
                        </div>
                        <p className="text-[10px] text-neutral-500 mt-0.5 truncate">
                          {c.status || c.state}
                        </p>
                      </div>

                      {c.name !== 'real-estate' && (
                        <button
                          type="button"
                          onClick={() => triggerHeal(c.name)}
                          disabled={isHealing}
                          className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-white dark:bg-charcoal-dark border border-neutral-300 dark:border-neutral-700 hover:border-amber-400 dark:hover:border-amber-500 text-neutral-700 dark:text-neutral-300 transition-colors flex items-center gap-1"
                          title="Restart container"
                        >
                          <RotateCw className={`w-3 h-3 ${isHealing ? 'animate-spin text-amber-500' : ''}`} />
                          <span>Restart</span>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Uptime Kuma Monitors */}
            <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-serif font-bold text-sm text-neutral-900 dark:text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-500" />
                  <span>Uptime Kuma Monitors ({monitors.length})</span>
                </h4>
                <span className="text-xs text-neutral-400">
                  Notification: Agent Hub Infra Guardian
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {monitors.map((m) => {
                  const isUp = m.status === 'UP';
                  return (
                    <div
                      key={m.id}
                      className="p-3.5 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                          <h5 className="font-bold text-xs text-neutral-900 dark:text-white truncate">
                            {m.name}
                          </h5>
                        </div>
                        <p className="text-[10px] text-neutral-500 mt-0.5 truncate">
                          {m.type?.toUpperCase()} • {m.ping_ms ? `${m.ping_ms}ms` : 'Healthy'}
                        </p>
                      </div>

                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isUp ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                      }`}>
                        {m.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        )}

      </div>

    </div>
  );
}
