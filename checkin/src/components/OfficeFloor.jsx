import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Server,
  RefreshCw,
  CheckCircle2,
  RotateCw,
  Terminal,
  ArrowRight,
  Cpu,
  Database,
  Sparkles,
  Search,
  Filter
} from 'lucide-react';

const FLOW_CATEGORIES = [
  { id: 'non_ha', label: 'Important (Non-HA)', color: 'indigo' },
  { id: 'all', label: 'All', color: 'neutral' },
  { id: 'finance', label: 'Finance & Tax', color: 'emerald' },
  { id: 'crm', label: 'CRM & Clients', color: 'blue' },
  { id: 'email', label: 'Email & Triage', color: 'violet' },
  { id: 'home_assistant', label: 'Home Assistant', color: 'cyan' },
  { id: 'infra', label: 'IT & Infra', color: 'amber' },
  { id: 'marketing', label: 'Marketing & CMA', color: 'rose' },
  { id: 'general', label: 'General', color: 'neutral' },
];

const AGENT_FILTERS = [
  'All Agents',
  'Marcus Vance',
  'Fiona Banks',
  'Victor Sterling',
  'Miles Miller',
  'Silas Drake',
  'Hannah Reed',
  'Ian Torres',
  'Maya Reyes',
  'Carter Hayes',
  'Audrey Chen',
];

const CATEGORY_BADGE_STYLES = {
  finance: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
  crm: 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300',
  email: 'bg-violet-100 text-violet-800 dark:bg-violet-950/60 dark:text-violet-300',
  home_assistant: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-300',
  infra: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
  marketing: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
  general: 'bg-neutral-200 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
};

const CATEGORY_LABELS = {
  finance: 'Finance & Tax',
  crm: 'CRM & Clients',
  email: 'Email & Triage',
  home_assistant: 'Home Assistant',
  infra: 'IT & Infra',
  marketing: 'Marketing & CMA',
  general: 'General',
};

export default function OfficeFloor() {
  const [flows, setFlows] = useState([]);
  const [flowStats, setFlowStats] = useState(null);
  const [containers, setContainers] = useState([]);
  const [monitors, setMonitors] = useState([]);
  const [selectedFlow, setSelectedFlow] = useState(null);
  const [activeView, setActiveView] = useState('inspector'); // 'inspector' | 'telemetry' | 'memory'
  const [selectedCategory, setSelectedCategory] = useState('non_ha');
  const [selectedAgentFilter, setSelectedAgentFilter] = useState('All Agents');
  const [historyLimit, setHistoryLimit] = useState(200);
  const [memoryStats, setMemoryStats] = useState(null);
  const [memorySearchQuery, setMemorySearchQuery] = useState('');
  const [memorySearchResults, setMemorySearchResults] = useState([]);
  const [memorySearching, setMemorySearching] = useState(false);
  const [newMemoryAgent, setNewMemoryAgent] = useState('manager');
  const [newMemoryCategory, setNewMemoryCategory] = useState('domain_knowledge');
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [savingMemory, setSavingMemory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [healingContainer, setHealingContainer] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');

  // Fetch categorized flows, stats, and telemetry data
  const refreshData = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: String(historyLimit) });
      if (selectedCategory === 'non_ha') {
        params.set('exclude_category', 'home_assistant');
      } else if (selectedCategory !== 'all') {
        params.set('category', selectedCategory);
      }
      if (selectedAgentFilter && selectedAgentFilter !== 'All Agents') {
        params.set('agent', selectedAgentFilter);
      }
      if (searchFilter.trim()) {
        params.set('search', searchFilter.trim());
      }

      const [flowsRes, statsRes, contRes, monRes, memRes] = await Promise.all([
        fetch(`/api/manager/office/flows?${params.toString()}`).then(r => r.json()).catch(() => []),
        fetch('/api/manager/office/flow-stats').then(r => r.json()).catch(() => null),
        fetch('/api/manager/office/containers').then(r => r.json()).catch(() => ({ containers: [] })),
        fetch('/api/manager/office/monitors').then(r => r.json()).catch(() => ({ monitors: [] })),
        fetch('/api/manager/memory/stats').then(r => r.json()).catch(() => null),
      ]);

      if (Array.isArray(flowsRes)) {
        setFlows(flowsRes);
        setSelectedFlow(prev => {
          if (prev && flowsRes.some(f => f.flow_id === prev.flow_id)) return prev;
          return flowsRes.length > 0 ? flowsRes[0] : null;
        });
      }
      if (statsRes && typeof statsRes.total === 'number') setFlowStats(statsRes);
      if (contRes?.containers) setContainers(contRes.containers);
      if (monRes?.monitors) setMonitors(monRes.monitors);
      if (memRes) setMemoryStats(memRes);
    } catch (err) {
      console.error('Failed to fetch agent logs:', err);
    } finally {
      setLoading(false);
    }
  }, [historyLimit, selectedCategory, selectedAgentFilter, searchFilter]);

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

  const handleSearchMemory = async (e) => {
    e?.preventDefault();
    if (!memorySearchQuery.trim()) return;
    setMemorySearching(true);
    try {
      const res = await fetch('/api/manager/memory/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: memorySearchQuery.trim(), top_k: 6 }),
      });
      const data = await res.json();
      setMemorySearchResults(data.matches || []);
    } catch (err) {
      alert(`Memory search error: ${err.message}`);
    } finally {
      setMemorySearching(false);
    }
  };

  const handleSaveMemory = async (e) => {
    e?.preventDefault();
    if (!newMemoryContent.trim()) return;
    setSavingMemory(true);
    try {
      const res = await fetch('/api/manager/memory/store', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: newMemoryAgent,
          category: newMemoryCategory,
          content: newMemoryContent.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) alert(`Store failed: ${data.detail || data.error}`);
      else {
        alert('Memory vectorized and stored in SQLite-vec brain!');
        setNewMemoryContent('');
        refreshData();
      }
    } catch (err) {
      alert(`Store error: ${err.message}`);
    } finally {
      setSavingMemory(false);
    }
  };

  const healthyContainers = containers.filter(c => c.state === 'running').length;
  const upMonitors = monitors.filter(m => m.status === 'UP').length;

  const getCategoryCount = (catId) => {
    if (!flowStats) return null;
    if (catId === 'all') return flowStats.total;
    if (catId === 'non_ha') return flowStats.non_ha_total;
    return flowStats.category_counts?.[catId] || 0;
  };

  const getAgentCount = (agentName) => {
    if (!flowStats) return null;
    if (agentName === 'All Agents') return flowStats.total;
    return flowStats.agent_counts?.[agentName] || 0;
  };

  const formatTimestamp = (isoStr) => {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr.slice(0, 19).replace('T', ' ');
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-ivory dark:bg-charcoal min-h-screen text-neutral-900 dark:text-neutral-100 transition-colors">
      
      {/* Top Banner & Control Bar */}
      <div className="bg-white/80 dark:bg-charcoal-dark/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 px-4 sm:px-8 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                <Terminal className="w-5 h-5" />
              </span>
              <h2 className="text-xl font-serif font-bold text-neutral-900 dark:text-white">
                Agent Query & Execution Logs
              </h2>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live Trace History
              </span>
            </div>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
              Full-space categorized query history, per-agent filtering, and step-by-step multi-agent execution traces.
            </p>
          </div>

          {/* Quick Metrics Bar & Controls */}
          <div className="flex items-center flex-wrap gap-2 sm:gap-4">
            
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-xl bg-neutral-100 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="text-neutral-400">Total Logs:</span>
                <span className="font-bold text-neutral-900 dark:text-neutral-100">{flowStats?.total ?? flows.length}</span>
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
                onClick={() => setActiveView('inspector')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all ${
                  activeView === 'inspector'
                    ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                    : 'text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Terminal className="w-3.5 h-3.5 text-indigo-500" />
                <span>Query Logs</span>
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
              <button
                type="button"
                onClick={() => setActiveView('memory')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all ${
                  activeView === 'memory'
                    ? 'bg-white dark:bg-charcoal-dark text-neutral-900 dark:text-white shadow-sm'
                    : 'text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Database className="w-3.5 h-3.5 text-purple-500" />
                <span>Vector Brain</span>
                {memoryStats?.total_memories > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
                    {memoryStats.total_memories}
                  </span>
                )}
              </button>
            </div>

            {/* Refresh Controls */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={refreshData}
                disabled={loading}
                className="p-2 rounded-lg bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                title="Refresh query logs"
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

      {/* Main Container */}
      <div className="max-w-7xl mx-auto w-full p-4 sm:p-6 flex-1 flex flex-col gap-5">

        {/* VIEW 1: FULL-SPACE CATEGORIZED & PER-AGENT QUERY LOGS */}
        {activeView === 'inspector' && (
          <div className="flex flex-col gap-4 flex-1">

            {/* Category & Agent Filter Console */}
            <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-4 shadow-sm flex flex-col gap-3">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                {/* Category Filter Pills */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-neutral-400 mr-1">
                    <Filter className="w-3 h-3" />
                    Category:
                  </span>
                  {FLOW_CATEGORIES.map((cat) => {
                    const cnt = getCategoryCount(cat.id);
                    const active = selectedCategory === cat.id;
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => setSelectedCategory(cat.id)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                          active
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                            : 'bg-neutral-50 dark:bg-charcoal text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                        }`}
                      >
                        <span>{cat.label}</span>
                        {cnt !== null && (
                          <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                            active ? 'bg-white/20 text-white' : 'bg-neutral-200/80 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
                          }`}>
                            {cnt}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Search + History Depth */}
                <div className="flex items-center gap-2 shrink-0">
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Search queries, tools, payloads..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <select
                    value={historyLimit}
                    onChange={(e) => setHistoryLimit(Number(e.target.value))}
                    className="px-2.5 py-1.5 text-xs font-semibold rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300"
                    title="Maximum history records to load"
                  >
                    <option value={100}>Last 100</option>
                    <option value={200}>Last 200</option>
                    <option value={500}>Last 500</option>
                  </select>
                </div>
              </div>

              {/* Per-Agent Filter Pills */}
              <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-neutral-100 dark:border-neutral-800">
                <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-400 mr-1">
                  Agent:
                </span>
                {AGENT_FILTERS.map((agName) => {
                  const cnt = getAgentCount(agName);
                  const active = selectedAgentFilter === agName;
                  return (
                    <button
                      key={agName}
                      type="button"
                      onClick={() => setSelectedAgentFilter(agName)}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all ${
                        active
                          ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                          : 'bg-white dark:bg-charcoal text-neutral-600 dark:text-neutral-300 border-neutral-200 dark:border-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                      }`}
                    >
                      <span>{agName}</span>
                      {cnt !== null && (
                        <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                          active ? 'bg-white/20 text-white' : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400'
                        }`}>
                          {cnt}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Split Logs & Inspector Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
              {/* Left Column: Deep History Flows List */}
              <div className="lg:col-span-5 flex flex-col">
                <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-4 shadow-sm flex flex-col gap-2 overflow-y-auto max-h-[78vh]">
                  <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-neutral-400 px-2 py-1">
                    <span>Showing {flows.length} Queries</span>
                    {selectedCategory === 'non_ha' && (
                      <span className="text-[10px] font-semibold text-indigo-500 normal-case">
                        HA noise hidden
                      </span>
                    )}
                  </div>

                  {flows.length === 0 ? (
                    <p className="text-xs text-neutral-500 p-6 text-center">
                      No matching queries found for the selected category/agent filter.
                    </p>
                  ) : (
                    flows.map((flow) => {
                      const isSelected = selectedFlow?.flow_id === flow.flow_id;
                      const catKey = flow.category || 'general';
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
                          <div className="flex items-center justify-between gap-2 text-xs mb-1">
                            <span className="font-bold text-neutral-900 dark:text-white truncate">
                              {flow.title}
                            </span>
                            <span className="text-[10px] text-neutral-400 font-mono shrink-0">
                              {formatTimestamp(flow.created_at)}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 flex-wrap text-[11px] text-neutral-500 dark:text-neutral-400 mb-2">
                            <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${CATEGORY_BADGE_STYLES[catKey] || CATEGORY_BADGE_STYLES.general}`}>
                              {CATEGORY_LABELS[catKey] || catKey}
                            </span>
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

        {/* VIEW 4: AGENT VECTOR MEMORY BRAIN */}
        {activeView === 'memory' && (
          <div className="flex flex-col gap-6">
            
            {/* Memory Header & Summary Stats */}
            <div className="rounded-2xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-200 dark:border-neutral-800 pb-4 mb-6">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400">
                      <Database className="w-5 h-5" />
                    </span>
                    <h3 className="text-lg font-serif font-bold text-neutral-900 dark:text-white">
                      Agent Vector Memory Database (agent_memory.db)
                    </h3>
                  </div>
                  <p className="text-xs text-neutral-500 mt-1">
                    Powered by sqlite-vec and FastEmbed (BAAI/bge-small-en-v1.5, 384 dims). Enables persistent institutional memory, comp retrieval, and continuous self-improvement across delegations.
                  </p>
                </div>

                <div className="flex items-center gap-4 text-xs">
                  <div className="px-3 py-1.5 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800">
                    <span className="text-neutral-500 dark:text-neutral-400">Total Memories:</span>{' '}
                    <strong className="text-purple-700 dark:text-purple-300 font-mono text-sm">{memoryStats?.total_memories || 0}</strong>
                  </div>
                </div>
              </div>

              {/* Vector Query Explorer */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Search Box */}
                <div className="flex flex-col gap-4">
                  <h4 className="font-bold text-sm text-neutral-900 dark:text-white flex items-center gap-2">
                    <Search className="w-4 h-4 text-purple-500" />
                    <span>Semantic Similarity Search</span>
                  </h4>
                  <form onSubmit={handleSearchMemory} className="flex gap-2">
                    <input
                      type="text"
                      value={memorySearchQuery}
                      onChange={(e) => setMemorySearchQuery(e.target.value)}
                      placeholder="e.g. Somerset view home price, container healing rule..."
                      className="flex-1 px-3 py-2 rounded-xl text-xs bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 focus:outline-hidden focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      type="submit"
                      disabled={memorySearching}
                      className="px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white transition-colors flex items-center gap-1.5 shadow-xs"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{memorySearching ? 'Searching...' : 'Vector Match'}</span>
                    </button>
                  </form>

                  {/* Results List */}
                  <div className="flex flex-col gap-2.5 mt-2">
                    {memorySearchResults.length === 0 ? (
                      <div className="text-xs text-neutral-400 p-4 border border-dashed border-neutral-200 dark:border-neutral-800 rounded-xl text-center">
                        Enter a natural language query above to test real-time vector matching.
                      </div>
                    ) : (
                      memorySearchResults.map((m) => (
                        <div
                          key={m.id}
                          className="p-3 rounded-xl bg-neutral-50 dark:bg-charcoal border border-neutral-200 dark:border-neutral-800 text-xs flex flex-col gap-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold uppercase tracking-wider text-[10px] text-purple-600 dark:text-purple-400">
                              [{m.agent_id}] • {m.category}
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-bold">
                              {Math.round(m.similarity * 100)}% Match
                            </span>
                          </div>
                          <p className="text-neutral-700 dark:text-neutral-300 font-medium">
                            {m.content}
                          </p>
                          <span className="text-[9px] text-neutral-400">
                            Recorded: {m.created_at} • Distance: {m.distance}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Teach New Vector Fact / Memory Form */}
                <div className="flex flex-col gap-4 border-t lg:border-t-0 lg:border-l border-neutral-200 dark:border-neutral-800 lg:pl-6 pt-4 lg:pt-0">
                  <h4 className="font-bold text-sm text-neutral-900 dark:text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-500" />
                    <span>Teach Knowledge into Vector Brain</span>
                  </h4>
                  <form onSubmit={handleSaveMemory} className="flex flex-col gap-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[11px] text-neutral-500 block mb-1">Target Specialist</label>
                        <select
                          value={newMemoryAgent}
                          onChange={(e) => setNewMemoryAgent(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg text-xs bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700"
                        >
                          <option value="manager">Marcus Vance (Manager)</option>
                          <option value="cma">Carter Hayes (CMA / Comps)</option>
                          <option value="it">Ian Torres (IT / DevOps)</option>
                          <option value="auditor">Audrey Chen (Auditor)</option>
                          <option value="intake">Miles Miller (Intake)</option>
                          <option value="finance">Fiona Banks (Finance)</option>
                          <option value="marketing">Maya Reyes (Marketing)</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[11px] text-neutral-500 block mb-1">Knowledge Category</label>
                        <select
                          value={newMemoryCategory}
                          onChange={(e) => setNewMemoryCategory(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg text-xs bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700"
                        >
                          <option value="domain_knowledge">Domain Knowledge</option>
                          <option value="market_intelligence">Market Intelligence</option>
                          <option value="operational_rule">Operational Rule</option>
                          <option value="client_preference">Client Preference</option>
                          <option value="past_resolution">Past Resolution Pattern</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="text-[11px] text-neutral-500 block mb-1">Fact / Resolution to Vectorize</label>
                      <textarea
                        rows={4}
                        value={newMemoryContent}
                        onChange={(e) => setNewMemoryContent(e.target.value)}
                        placeholder="e.g. When client asks for waterfront homes in Kirkland, check Lake Washington parcel setback rules..."
                        className="w-full px-3 py-2 rounded-xl text-xs bg-neutral-50 dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={savingMemory}
                      className="self-end px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors flex items-center gap-1.5 shadow-xs"
                    >
                      <Database className="w-3.5 h-3.5" />
                      <span>{savingMemory ? 'Vectorizing...' : 'Store in Vector Memory'}</span>
                    </button>
                  </form>
                </div>

              </div>
            </div>

          </div>
        )}

      </div>

    </div>
  );
}
