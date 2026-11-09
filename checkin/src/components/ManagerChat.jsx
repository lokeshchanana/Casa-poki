import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Bot,
  User,
  Trash2,
  Sparkles,
  Copy,
  Check,
  Square,
  Cpu,
  ShieldCheck,
  Workflow,
  BrainCircuit,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Gauge,
  FileCode2,
  Plus,
  RefreshCw,
  ClipboardList
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  {
    label: 'Inspect n8n Workflows',
    prompt: 'What workflows are currently available in n8n?'
  },
  {
    label: 'CRM Lookup (Active n8n)',
    prompt: 'Search for contacts named Surbhi in Relaticle CRM'
  },
  {
    label: 'Test Missing Workflow (GBP)',
    prompt: 'Post a weekly market update on Google Business Profile for Bellevue'
  },
  {
    label: 'Test Missing Workflow (Mailman)',
    prompt: 'Check unread emails in my mailbox and summarize urgent client inquiries'
  },
  {
    label: 'Test Inactive Workflow (Calendar->GBP)',
    prompt: 'Sync open house events from Google Calendar to Google Business Profile'
  },
  {
    label: 'Teach Agent Rule',
    prompt: 'Remember: always include the contact ID and phone format in E.164 when reporting CRM updates'
  }
];

function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements = [];
  let inList = false;
  let listItems = [];
  let inCodeBlock = false;
  let codeLines = [];

  const parseInline = (str) => {
    const parts = [];
    const regex = /(\*\*.*?\*\*|`[^`]+`)/g;
    let match;
    let lastIndex = 0;
    let keyIdx = 0;

    while ((match = regex.exec(str)) !== null) {
      if (match.index > lastIndex) {
        parts.push(str.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(
          <strong key={`b-${keyIdx++}`} className="font-semibold text-neutral-950 dark:text-white">
            {token.slice(2, -2)}
          </strong>
        );
      } else if (token.startsWith('`') && token.endsWith('`')) {
        parts.push(
          <code
            key={`c-${keyIdx++}`}
            className="px-1.5 py-0.5 text-[11px] font-mono bg-neutral-200/80 dark:bg-neutral-900 text-indigo-700 dark:text-indigo-300 rounded"
          >
            {token.slice(1, -1)}
          </code>
        );
      }
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < str.length) {
      parts.push(str.substring(lastIndex));
    }

    return parts.length > 0 ? parts : str;
  };

  const flushList = () => {
    if (inList && listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc pl-5 my-2 space-y-1">
          {listItems.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {parseInline(item)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      flushList();
      if (inCodeBlock) {
        elements.push(
          <pre
            key={`pre-${index}`}
            className="my-2 p-3 rounded-xl bg-neutral-900 text-neutral-100 font-mono text-[11px] overflow-x-auto border border-neutral-800"
          >
            {codeLines.join('\n')}
          </pre>
        );
        codeLines = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    if (!trimmed) {
      flushList();
      elements.push(<div key={`space-${index}`} className="h-2" />);
      return;
    }

    if (trimmed === '---') {
      flushList();
      elements.push(
        <hr key={`hr-${index}`} className="my-3 border-neutral-200 dark:border-neutral-700/80" />
      );
      return;
    }

    if (trimmed.startsWith('> ')) {
      flushList();
      elements.push(
        <blockquote
          key={`bq-${index}`}
          className="my-2 pl-3 border-l-2 border-indigo-500 italic text-neutral-700 dark:text-neutral-300 bg-indigo-50/50 dark:bg-indigo-950/20 py-1.5 pr-2 rounded-r-lg"
        >
          {parseInline(trimmed.substring(2))}
        </blockquote>
      );
      return;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      inList = true;
      listItems.push(trimmed.substring(2));
      return;
    }

    if (/^\d+\.\s/.test(trimmed)) {
      inList = true;
      listItems.push(trimmed.replace(/^\d+\.\s/, ''));
      return;
    }

    flushList();

    if (trimmed.startsWith('#### ')) {
      elements.push(
        <h5
          key={`h5-${index}`}
          className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mt-3 mb-1"
        >
          {parseInline(trimmed.substring(5))}
        </h5>
      );
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <h4
          key={`h4-${index}`}
          className="text-sm font-serif font-bold text-neutral-900 dark:text-neutral-100 mt-3 mb-1"
        >
          {parseInline(trimmed.substring(4))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3
          key={`h3-${index}`}
          className="text-base font-serif font-bold text-neutral-900 dark:text-neutral-100 mt-4 mb-1.5 border-b border-neutral-200 dark:border-neutral-800 pb-1"
        >
          {parseInline(trimmed.substring(3))}
        </h3>
      );
    } else {
      elements.push(
        <p key={`p-${index}`} className="leading-relaxed my-1">
          {parseInline(line)}
        </p>
      );
    }
  });

  flushList();
  return elements;
}

export default function ManagerChat({ onBackToCheckIn }) {
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('manager_chat_messages_v1');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return [
      {
        id: 'welcome',
        role: 'assistant',
        content:
          "### Multi-Agent Manager Hub Online\n\nI am your **Central Manager Agent** powered directly by **Antigravity** with deep codebase context and full specialist team delegation.\n\nHere is how my team handles your instructions:\n- **Marcus Vance (Manager):** Analyzes your request, routes tasks, and coordinates specialists in real time.\n- **Silas Drake (Mailman):** Connects to `lokesh@lokeshchanana.com`, triages inbox messages, and drafts responses (draft-only policy with your verified signature).\n- **Miles Miller (Intake):** Manages Twenty CRM contacts, notes, and pipelines.\n- **Fiona Banks (Finance):** Records invoices and bills into Bigcapital.\n- **Carter Hayes (CMA):** Real estate valuations and MLS comps.\n- **Maya Reyes (Marketing):** Property marketing and social campaigns.\n- **Ian Torres (IT):** Live monitoring, container health, and infrastructure self-healing.\n- **Audrey Chen (Auditor):** Real-time quality verification and Zero Stray Communications compliance.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        trace: [],
        tokensUsed: 0,
        tokenBudget: 2000
      }
    ];
  });

  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgentPhase, setActiveAgentPhase] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [showPrompts, setShowPrompts] = useState(true);
  const [activeDrawer, setActiveDrawer] = useState(null); // 'workflows' | 'backlog' | 'learning' | null
  const [expandedTraces, setExpandedTraces] = useState({});
  const [dashboardData, setDashboardData] = useState(null);
  const [newLessonAgent, setNewLessonAgent] = useState('manager');
  const [newLessonRule, setNewLessonRule] = useState('');
  const [abortController, setAbortController] = useState(null);

  const [sessionId] = useState(() => {
    let sid = localStorage.getItem('manager_chat_session_id');
    if (!sid) {
      sid = 'mgr_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
      localStorage.setItem('manager_chat_session_id', sid);
    }
    return sid;
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const getApiBase = () => {
    if (
      window.location.origin.includes('checkin.lokeshchanana.com') ||
      window.location.origin.includes('192.168.1.240') ||
      window.location.port === '8091'
    ) {
      return '/api/manager';
    }
    return 'http://192.168.1.240:8094/api/manager';
  };

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${getApiBase()}/dashboard`);
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
      }
    } catch (e) {
      console.error('Failed to load Manager dashboard:', e);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem('manager_chat_messages_v1', JSON.stringify(messages));
    } catch (e) {}
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming, activeAgentPhase]);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleTrace = (msgId) => {
    setExpandedTraces((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleClearHistory = () => {
    if (window.confirm('Clear current Manager chat conversation?')) {
      const resetMessages = [
        {
          id: 'welcome-' + Date.now(),
          role: 'assistant',
          content:
            'Manager session refreshed. Ready to route tasks across IT Agent (n8n) and Auditor Agent.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          trace: [],
          tokensUsed: 0,
          tokenBudget: 2000
        }
      ];
      setMessages(resetMessages);
      localStorage.setItem('manager_chat_messages_v1', JSON.stringify(resetMessages));
    }
  };

  const handleAddLesson = async (e) => {
    e.preventDefault();
    if (!newLessonRule.trim()) return;
    try {
      const res = await fetch(`${getApiBase()}/lessons`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: newLessonAgent,
          rule: newLessonRule.trim()
        })
      });
      if (res.ok) {
        setNewLessonRule('');
        fetchDashboard();
      }
    } catch (err) {
      console.error('Failed to add lesson:', err);
    }
  };

  const handleDeleteLesson = async (id) => {
    try {
      const res = await fetch(`${getApiBase()}/lessons/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchDashboard();
      }
    } catch (err) {
      console.error('Failed to delete lesson:', err);
    }
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setIsStreaming(false);
      setActiveAgentPhase(null);
      setAbortController(null);
    }
  };

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim();
    if (!text || isStreaming) return;

    setInput('');
    const userMsgId = 'user_' + Date.now();
    const assistantMsgId = 'mgr_' + Date.now();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const updated = [
      ...messages,
      { id: userMsgId, role: 'user', content: text, timestamp: timeStr },
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: timeStr,
        isThinking: true,
        trace: [],
        tokensUsed: 0,
        tokenBudget: 2000,
        specCreated: null
      }
    ];

    setMessages(updated);
    setExpandedTraces((prev) => ({ ...prev, [assistantMsgId]: true }));
    setIsStreaming(true);
    setActiveAgentPhase({
      agent: 'manager',
      message: 'Manager Agent is triaging your request...'
    });

    const controller = new AbortController();
    setAbortController(controller);

    try {
      const response = await fetch(`${getApiBase()}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatInput: text,
          sessionId: sessionId,
          tokenBudget: 2000
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`Manager Hub returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulatedText = '';
      let currentTraces = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          try {
            const event = JSON.parse(trimmed);
            if (event.type === 'agent_status') {
              setActiveAgentPhase({
                agent: event.agent,
                phase: event.phase,
                message: event.message
              });
            } else if (event.type === 'agent_trace' && event.trace) {
              currentTraces = [...currentTraces, event.trace];
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, trace: currentTraces } : m
                )
              );
            } else if (event.type === 'item' && typeof event.content === 'string') {
              accumulatedText += event.content;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, content: accumulatedText, isThinking: false }
                    : m
                )
              );
            } else if (event.type === 'complete') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        trace: event.trace || currentTraces,
                        tokensUsed: event.tokens_used || 0,
                        tokenBudget: event.token_budget || 2000,
                        specCreated: event.spec_created || null,
                        isThinking: false
                      }
                    : m
                )
              );
            }
          } catch (e) {
            console.warn('Non-JSON stream line:', trimmed);
          }
        }
      }

      if (!accumulatedText.trim()) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content:
                    '⚠️ Stream ended before final output was received. Please retry your request.',
                  isThinking: false
                }
              : m
          )
        );
      }

      fetchDashboard();
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: (m.content || '') + '\n\n*(Execution stopped)*', isThinking: false }
              : m
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `⚠️ Error contacting Multi-Agent Manager Hub: ${err.message}`,
                  isThinking: false
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      setActiveAgentPhase(null);
      setAbortController(null);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const activeWorkflowsCount =
    dashboardData?.workflows?.filter((w) => w.active)?.length ?? 3;
  const backlogCount = dashboardData?.missing_workflows_backlog?.length ?? 0;
  const lessonsCount = dashboardData?.lessons?.length ?? 0;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-5xl mx-auto w-full bg-white dark:bg-charcoal-dark border-x border-neutral-200 dark:border-neutral-800 shadow-xl transition-colors">
      {/* Top Multi-Agent Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/90 dark:bg-charcoal/90 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 via-violet-600 to-cyan-600 flex items-center justify-center text-white shadow-md">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <span
              className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 border-2 border-white dark:border-charcoal-dark rounded-full"
              title="Manager + IT + Auditor Active"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">
                Central Manager Agent
              </h2>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold bg-indigo-100 dark:bg-indigo-950/70 text-indigo-800 dark:text-indigo-300 rounded border border-indigo-300 dark:border-indigo-800">
                Manager • IT • Auditor
              </span>
            </div>
            <p className="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1">
                <Workflow className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                {activeWorkflowsCount} Active n8n Workflows
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1">
                <Gauge className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                Budget: 2,000 tok/task
              </span>
            </p>
          </div>
        </div>

        {/* Drawer & Action Buttons */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {onBackToCheckIn && (
            <button
              type="button"
              onClick={onBackToCheckIn}
              className="p-2 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-800 rounded-lg transition-colors text-xs flex items-center gap-1.5 font-medium border border-neutral-300 dark:border-neutral-700"
              title="Return to Open House Check-In"
            >
              <ClipboardList className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="hidden md:inline">Check-In</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setActiveDrawer(activeDrawer === 'workflows' ? null : 'workflows')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 border ${
              activeDrawer === 'workflows'
                ? 'bg-cyan-600 text-white border-cyan-600'
                : 'bg-white dark:bg-charcoal border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:border-cyan-500'
            }`}
            title="Inspect IT Agent's n8n Workflow Catalog"
          >
            <Workflow className="w-3.5 h-3.5" />
            <span>n8n ({activeWorkflowsCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveDrawer(activeDrawer === 'backlog' ? null : 'backlog')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 border ${
              activeDrawer === 'backlog'
                ? 'bg-amber-600 text-white border-amber-600'
                : 'bg-white dark:bg-charcoal border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:border-amber-500'
            }`}
            title="Missing n8n Workflow Specs for Antigravity"
          >
            <FileCode2 className="w-3.5 h-3.5 text-amber-500" />
            <span>Specs ({backlogCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveDrawer(activeDrawer === 'learning' ? null : 'learning')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 border ${
              activeDrawer === 'learning'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white dark:bg-charcoal border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:border-indigo-500'
            }`}
            title="Agent Learned Rules & Token Rationing Ledger"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
            <span>Rules ({lessonsCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setShowPrompts((prev) => !prev)}
            className={`p-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
              showPrompts
                ? 'bg-neutral-200 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'
                : 'text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800'
            }`}
            title="Toggle suggested prompts"
          >
            <Sparkles className="w-4 h-4 text-amber-500" />
          </button>

          <button
            type="button"
            onClick={handleClearHistory}
            className="p-2 text-neutral-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors text-xs"
            title="Clear conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Collapsible Top System Drawers */}
      {activeDrawer === 'workflows' && (
        <div className="p-4 bg-neutral-50 dark:bg-charcoal border-b border-neutral-200 dark:border-neutral-800 max-h-72 overflow-y-auto text-xs">
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="font-bold text-neutral-900 dark:text-white flex items-center gap-1.5">
              <Workflow className="w-4 h-4 text-cyan-500" />
              IT Agent — Live n8n Workflow Registry
            </h3>
            <button
              type="button"
              onClick={fetchDashboard}
              className="text-[11px] text-cyan-600 dark:text-cyan-400 flex items-center gap-1 hover:underline"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {(dashboardData?.workflows || []).map((wf) => (
              <div
                key={wf.id}
                className="p-3 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 flex flex-col justify-between gap-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-bold text-neutral-900 dark:text-neutral-100">
                      {wf.name}
                    </div>
                    <div className="text-[10px] font-mono text-neutral-400">
                      ID: {wf.id} • Domain: {wf.domain}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      wf.active
                        ? 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                        : 'bg-amber-100 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                    }`}
                  >
                    {wf.active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="text-[11px] text-neutral-600 dark:text-neutral-400 leading-snug">
                  {wf.summary}
                </p>
                {wf.tools && wf.tools.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {wf.tools.map((t, i) => (
                      <span
                        key={i}
                        className="px-1.5 py-0.5 text-[10px] font-mono bg-neutral-100 dark:bg-neutral-800 rounded text-neutral-600 dark:text-neutral-300"
                      >
                        {t.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeDrawer === 'backlog' && (
        <div className="p-4 bg-neutral-50 dark:bg-charcoal border-b border-neutral-200 dark:border-neutral-800 max-h-80 overflow-y-auto text-xs">
          <div className="flex items-center justify-between mb-2.5">
            <div>
              <h3 className="font-bold text-neutral-900 dark:text-white flex items-center gap-1.5">
                <FileCode2 className="w-4 h-4 text-amber-500" />
                Missing n8n Workflow Specs (Ready for Antigravity)
              </h3>
              <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
                Generated automatically when the Auditor reports a missing n8n capability to the Manager.
              </p>
            </div>
          </div>

          {(dashboardData?.missing_workflows_backlog || []).length === 0 ? (
            <div className="p-4 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 text-neutral-500 text-center">
              No missing workflow specs logged yet. Try asking the Manager to perform a task that isn't in n8n yet!
            </div>
          ) : (
            <div className="space-y-2.5">
              {(dashboardData?.missing_workflows_backlog || []).map((spec) => (
                <div
                  key={spec.slug}
                  className="p-3 rounded-xl bg-white dark:bg-charcoal-dark border border-amber-300/70 dark:border-amber-800/60 flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-bold text-neutral-900 dark:text-white flex items-center gap-2">
                      <span>{spec.workflow_name}</span>
                      <span className="px-1.5 py-0.5 text-[10px] font-mono bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 rounded">
                        {spec.domain}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopy(spec.slug, spec.antigravity_prompt)}
                      className="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-semibold flex items-center gap-1 shadow-sm"
                    >
                      {copiedId === spec.slug ? (
                        <>
                          <Check className="w-3 h-3" /> Copied Prompt
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" /> Copy Antigravity Prompt
                        </>
                      )}
                    </button>
                  </div>
                  <div className="text-[11px] text-neutral-600 dark:text-neutral-400">
                    <strong>Auditor Gap Report:</strong> {spec.auditor_findings}
                  </div>
                  <div className="text-[10px] font-mono text-neutral-500">
                    Spec File: {spec.host_path}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeDrawer === 'learning' && (
        <div className="p-4 bg-neutral-50 dark:bg-charcoal border-b border-neutral-200 dark:border-neutral-800 max-h-80 overflow-y-auto text-xs space-y-4">
          {/* Token Rationing Summary */}
          <div>
            <h3 className="font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 mb-2">
              <Gauge className="w-4 h-4 text-emerald-500" />
              Token Rationing & Throughput Ledger (~500 tok/s Cap)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="p-2.5 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800">
                <div className="text-[10px] text-neutral-400 uppercase">Total Tokens Used</div>
                <div className="text-sm font-bold text-neutral-900 dark:text-white font-mono">
                  {dashboardData?.token_stats?.total_tokens_all_time || 0}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800">
                <div className="text-[10px] text-neutral-400 uppercase">Avg Speed</div>
                <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                  {dashboardData?.token_stats?.avg_tokens_per_sec || 0} tok/s
                </div>
              </div>
              {(dashboardData?.token_stats?.by_agent || []).map((ag) => (
                <div
                  key={ag.agent}
                  className="p-2.5 rounded-xl bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800"
                >
                  <div className="text-[10px] text-neutral-400 uppercase">{ag.agent}</div>
                  <div className="text-xs font-bold text-neutral-900 dark:text-white font-mono">
                    {ag.total_tokens} tok ({ag.calls} runs)
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Learned Rules Registry */}
          <div>
            <h3 className="font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 mb-2">
              <ShieldCheck className="w-4 h-4 text-indigo-500" />
              Agent Learned Rules & Prompt Fine-Tuning
            </h3>
            <form onSubmit={handleAddLesson} className="flex gap-2 mb-3">
              <select
                value={newLessonAgent}
                onChange={(e) => setNewLessonAgent(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-charcoal-dark border border-neutral-300 dark:border-neutral-700 text-xs font-semibold"
              >
                <option value="manager">manager</option>
                <option value="it_agent">it_agent</option>
                <option value="auditor">auditor</option>
                <option value="crm">crm</option>
                <option value="marketing">marketing</option>
              </select>
              <input
                type="text"
                value={newLessonRule}
                onChange={(e) => setNewLessonRule(e.target.value)}
                placeholder="Add a rule or lesson for this agent to always follow..."
                className="flex-1 px-3 py-1.5 rounded-lg bg-white dark:bg-charcoal-dark border border-neutral-300 dark:border-neutral-700 text-xs"
              />
              <button
                type="submit"
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" /> Add Rule
              </button>
            </form>

            <div className="space-y-1.5">
              {(dashboardData?.lessons || []).map((l) => (
                <div
                  key={l.id}
                  className="p-2 rounded-lg bg-white dark:bg-charcoal-dark border border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold bg-indigo-100 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 rounded">
                      {l.agent_name}
                    </span>
                    <span className="text-neutral-700 dark:text-neutral-300">{l.rule}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteLesson(l.id)}
                    className="text-neutral-400 hover:text-red-500 p-1"
                    title="Delete rule"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Suggested Prompts Drawer */}
      {showPrompts && (
        <div className="px-4 py-2.5 bg-neutral-100/70 dark:bg-charcoal/50 border-b border-neutral-200 dark:border-neutral-800 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400 whitespace-nowrap">
            Try Pipeline:
          </span>
          <div className="flex items-center gap-2">
            {SUGGESTED_PROMPTS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(item.prompt)}
                disabled={isStreaming}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-white dark:bg-charcoal border border-neutral-200 dark:border-neutral-700 hover:border-indigo-500 dark:hover:border-indigo-400 text-neutral-700 dark:text-neutral-300 text-[11px] font-medium transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
        {messages.map((m) => {
          const isUser = m.role === 'user';
          const hasTrace = Array.isArray(m.trace) && m.trace.length > 0;
          const isTraceOpen = !!expandedTraces[m.id];

          return (
            <div
              key={m.id}
              className={`flex gap-3 sm:gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-cyan-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                  <BrainCircuit className="w-4 h-4" />
                </div>
              )}

              <div
                className={`flex flex-col ${
                  isUser ? 'items-end' : 'items-start'
                } max-w-[90%] sm:max-w-[82%] w-full`}
              >
                {/* Multi-Agent Execution Trace Card */}
                {!isUser && hasTrace && (
                  <div className="w-full mb-2 rounded-xl border border-indigo-200/80 dark:border-indigo-900/60 bg-indigo-50/40 dark:bg-indigo-950/20 overflow-hidden text-xs">
                    <button
                      type="button"
                      onClick={() => toggleTrace(m.id)}
                      className="w-full px-3 py-2 flex items-center justify-between gap-2 text-left hover:bg-indigo-100/50 dark:hover:bg-indigo-900/30 transition-colors"
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        {isTraceOpen ? (
                          <ChevronDown className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                        )}
                        <span className="font-bold text-indigo-950 dark:text-indigo-200">
                          Agent Execution Pipeline ({m.trace.length} steps)
                        </span>
                        <span className="px-1.5 py-0.5 text-[10px] font-mono bg-white dark:bg-charcoal rounded border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300">
                          Tokens: {m.tokensUsed || 0} / {m.tokenBudget || 2000}
                        </span>
                      </div>
                      {m.specCreated && (
                        <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 rounded-full border border-amber-300 dark:border-amber-800">
                          Antigravity Spec Created
                        </span>
                      )}
                    </button>

                    {isTraceOpen && (
                      <div className="p-3 border-t border-indigo-200/60 dark:border-indigo-900/50 space-y-2 bg-white/80 dark:bg-charcoal-dark/80">
                        {m.trace.map((t, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50/70 dark:bg-charcoal/60 flex flex-col gap-1"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-1.5 font-bold text-neutral-900 dark:text-neutral-100">
                                <span className="w-4 h-4 rounded-full bg-indigo-600 text-white text-[10px] flex items-center justify-center">
                                  {t.step}
                                </span>
                                <span>{t.agent}</span>
                                <span className="text-[11px] font-normal text-neutral-500">
                                  — {t.role}
                                </span>
                              </div>
                              {t.metrics && t.metrics.total_tokens > 0 && (
                                <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
                                  {t.metrics.total_tokens} tok • {t.metrics.tokens_per_sec} tok/s
                                </span>
                              )}
                            </div>

                            {t.decision && (
                              <div className="text-[11px] text-neutral-600 dark:text-neutral-300 pl-5">
                                Intent: <code className="font-mono">{t.decision.intent}</code> • Domain:{' '}
                                <code className="font-mono">{t.decision.target_domain}</code> → Delegated to{' '}
                                <strong>{t.decision.delegated_to}</strong>
                              </div>
                            )}

                            {t.result && (
                              <div className="text-[11px] text-neutral-600 dark:text-neutral-300 pl-5 flex items-center gap-1.5 flex-wrap">
                                <span>n8n Status:</span>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                                    t.result.status === 'EXECUTED_SUCCESS' ||
                                    t.result.status === 'INVENTORY_REPORT'
                                      ? 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300'
                                      : 'bg-amber-100 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300'
                                  }`}
                                >
                                  {t.result.status}
                                </span>
                                {t.result.workflow_name && (
                                  <span>
                                    Workflow: <strong>{t.result.workflow_name}</strong>
                                  </span>
                                )}
                              </div>
                            )}

                            {t.report && (
                              <div className="text-[11px] text-neutral-600 dark:text-neutral-300 pl-5">
                                <span className="inline-flex items-center gap-1 font-semibold">
                                  {t.report.audit_status === 'PASS' ? (
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                                  ) : (
                                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                                  )}
                                  Auditor Verdict: {t.report.audit_status}
                                </span>{' '}
                                — {t.report.findings}
                              </div>
                            )}

                            {t.action_taken && (
                              <div className="text-[11px] text-indigo-700 dark:text-indigo-300 pl-5 font-medium">
                                Action: {t.action_taken}
                              </div>
                            )}
                          </div>
                        ))}

                        {m.specCreated && (
                          <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-800 flex items-center justify-between gap-2">
                            <div className="text-[11px] text-amber-900 dark:text-amber-200">
                              <strong>Ready for Antigravity:</strong>{' '}
                              <code className="font-mono">{m.specCreated.file_name}</code>
                            </div>
                            <button
                              type="button"
                              onClick={() =>
                                handleCopy(`spec_${m.id}`, m.specCreated.antigravity_prompt)
                              }
                              className="px-2.5 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-semibold flex items-center gap-1 flex-shrink-0"
                            >
                              {copiedId === `spec_${m.id}` ? (
                                <>
                                  <Check className="w-3 h-3" /> Copied
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" /> Copy Prompt for Antigravity
                                </>
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Main Message Bubble */}
                <div
                  className={`p-3.5 sm:p-4 rounded-2xl text-xs sm:text-sm font-sans relative group ${
                    isUser
                      ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded-br-none shadow-md'
                      : 'bg-neutral-100 dark:bg-neutral-800/80 text-neutral-900 dark:text-neutral-100 border border-neutral-200 dark:border-neutral-700/60 rounded-bl-none shadow-sm w-full'
                  }`}
                >
                  {m.isThinking && !m.content ? (
                    <div className="flex items-center gap-2.5 py-1 text-neutral-600 dark:text-neutral-300 text-xs">
                      <div className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                      <span className="font-medium">
                        {activeAgentPhase?.message ||
                          'Orchestrating Manager → IT Agent → Auditor...'}
                      </span>
                    </div>
                  ) : (
                    <div>{renderMarkdown(m.content)}</div>
                  )}

                  {!isUser && m.content && (
                    <button
                      type="button"
                      onClick={() => handleCopy(m.id, m.content)}
                      className="absolute top-2 right-2 p-1 rounded hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Copy response"
                    >
                      {copiedId === m.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-1 px-1">
                  <span className="text-[10px] text-neutral-400 font-mono">{m.timestamp}</span>
                </div>
              </div>

              {isUser && (
                <div className="w-8 h-8 rounded-lg bg-neutral-800 dark:bg-neutral-200 text-white dark:text-neutral-900 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Bar */}
      <div className="p-3 sm:p-4 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-charcoal/50">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative flex items-center gap-2"
        >
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Instruct Manager Agent (e.g. Search CRM, check n8n workflows, post to GBP, or 'Remember: ...')"
              className="w-full bg-white dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 text-xs sm:text-sm text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none shadow-sm transition-all"
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
          </div>

          {isStreaming ? (
            <button
              type="button"
              onClick={handleStop}
              className="h-11 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-md flex-shrink-0"
              title="Stop execution"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span className="hidden sm:inline">Stop</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="h-11 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 text-white font-bold text-xs flex items-center gap-1.5 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Delegate</span>
            </button>
          )}
        </form>

        <p className="text-[10px] text-neutral-400 text-center mt-2 font-sans">
          Pipeline: <strong>Manager</strong> (Routing & Learning) → <strong>IT Agent</strong> (n8n Catalog & Webhooks) → <strong>Auditor</strong> (Quality & Missing Workflow Spec).
        </p>
      </div>
    </div>
  );
}
