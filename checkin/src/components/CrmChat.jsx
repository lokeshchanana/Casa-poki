import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Bot, 
  User, 
  Trash2, 
  RotateCcw, 
  Sparkles, 
  Copy, 
  Check, 
  Square, 
  Database, 
  Cpu, 
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ClipboardList
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  { label: 'Search Contacts', prompt: 'Search for contacts named Surbhi in CRM' },
  { label: 'Update Phone', prompt: 'Update phone number for [Contact Name] to +12065550199' },
  { label: 'Check Tasks', prompt: 'List recent follow-up tasks from today\'s open house' },
  { label: 'Toggle Email', prompt: 'Change can email permission for [Contact Name] to True' },
  { label: 'Add Contact', prompt: 'Create a new contact named Alex Miller with email alex@example.com and phone (206) 555-0144' },
  { label: 'List Deals', prompt: 'List active opportunities and pipeline stages in CRM' }
];

function renderMarkdown(text) {
  if (!text) return null;

  // Split into lines
  const lines = text.split('\n');
  const elements = [];
  let inList = false;
  let listItems = [];

  const flushList = () => {
    if (inList && listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc pl-5 my-2 space-y-1">
          {listItems.map((item, idx) => (
            <li key={idx} className="leading-relaxed">{parseInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  const parseInline = (str) => {
    // Process bold **text**
    const parts = [];
    let remaining = str;
    let keyIdx = 0;

    // Replace bold **text**
    const regex = /\*\*(.*?)\*\*/g;
    let match;
    let lastIndex = 0;

    while ((match = regex.exec(str)) !== null) {
      if (match.index > lastIndex) {
        parts.push(str.substring(lastIndex, match.index));
      }
      parts.push(
        <strong key={`b-${keyIdx++}`} className="font-semibold text-neutral-950 dark:text-white">
          {match[1]}
        </strong>
      );
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < str.length) {
      parts.push(str.substring(lastIndex));
    }

    return parts.length > 0 ? parts : str;
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      elements.push(<div key={`space-${index}`} className="h-2" />);
      return;
    }

    // Bullet item
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      inList = true;
      listItems.push(trimmed.substring(2));
      return;
    }

    // Numbered item
    if (/^\d+\.\s/.test(trimmed)) {
      inList = true;
      listItems.push(trimmed.replace(/^\d+\.\s/, ''));
      return;
    }

    flushList();

    // Headers
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h4-${index}`} className="text-sm font-serif font-bold text-neutral-900 dark:text-neutral-100 mt-3 mb-1">
          {parseInline(trimmed.substring(4))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={`h3-${index}`} className="text-base font-serif font-bold text-neutral-900 dark:text-neutral-100 mt-4 mb-1.5 border-b border-neutral-200 dark:border-neutral-800 pb-1">
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

export default function CrmChat({ onBackToCheckIn }) {
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('crm_chat_messages');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return [
      {
        id: 'welcome',
        role: 'assistant',
        content: "Hello Loki! I am your Relaticle CRM AI Assistant powered by local Ollama.\n\nI can directly search contacts, update phone numbers & emails, create new leads, manage follow-up tasks, and look up notes in your CRM. What would you like to do?",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ];
  });

  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [showPrompts, setShowPrompts] = useState(true);
  const [abortController, setAbortController] = useState(null);

  const [sessionId] = useState(() => {
    let sid = localStorage.getItem('crm_chat_session_id');
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
      localStorage.setItem('crm_chat_session_id', sid);
    }
    return sid;
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem('crm_chat_messages', JSON.stringify(messages));
    } catch (e) {}
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearHistory = () => {
    if (window.confirm("Clear current CRM chat conversation?")) {
      const resetMessages = [
        {
          id: 'welcome-' + Date.now(),
          role: 'assistant',
          content: "Chat session refreshed. How can I help you with your Relaticle CRM records today?",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ];
      setMessages(resetMessages);
      localStorage.setItem('crm_chat_messages', JSON.stringify(resetMessages));
      const newSid = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
      localStorage.setItem('crm_chat_session_id', newSid);
    }
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setIsStreaming(false);
      setAbortController(null);
    }
  };

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim();
    if (!text || isStreaming) return;

    setInput('');
    const userMsgId = 'user_' + Date.now();
    const assistantMsgId = 'asst_' + Date.now();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const updated = [
      ...messages,
      { id: userMsgId, role: 'user', content: text, timestamp: timeStr },
      { id: assistantMsgId, role: 'assistant', content: '', timestamp: timeStr, isThinking: true }
    ];

    setMessages(updated);
    setIsStreaming(true);

    const controller = new AbortController();
    setAbortController(controller);

    const webhookUrl = (window.location.origin.includes('checkin.lokeshchanana.com') || window.location.origin.includes('192.168.1.240') || window.location.port === '8091')
      ? '/api/crm-chat'
      : 'https://n8n.lokeshchanana.com/webhook/relaticle-crm-chat/chat';

    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'sendMessage',
          chatInput: text,
          sessionId: sessionId
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`CRM Assistant returned error ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulatedText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep remainder

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          try {
            const data = JSON.parse(trimmed);
            if (data.type === 'item' && typeof data.content === 'string') {
              accumulatedText += data.content;
              setMessages(prev => prev.map(m => 
                m.id === assistantMsgId 
                  ? { ...m, content: accumulatedText, isThinking: false }
                  : m
              ));
            } else if (data.type === 'error') {
              accumulatedText += `\n\n[Error: ${data.message || 'Workflow processing error'}]`;
              setMessages(prev => prev.map(m => 
                m.id === assistantMsgId 
                  ? { ...m, content: accumulatedText, isThinking: false }
                  : m
              ));
            }
          } catch (e) {
            // Not a JSON line, append directly if it's text
            if (!trimmed.startsWith('{')) {
              accumulatedText += trimmed + ' ';
              setMessages(prev => prev.map(m => 
                m.id === assistantMsgId 
                  ? { ...m, content: accumulatedText, isThinking: false }
                  : m
              ));
            }
          }
        }
      }

      // If finished and no content received
      if (!accumulatedText.trim()) {
        setMessages(prev => prev.map(m => 
          m.id === assistantMsgId 
            ? { ...m, content: "Request processed, but no text response was generated by the CRM workflow.", isThinking: false }
            : m
        ));
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(m => 
          m.id === assistantMsgId 
            ? { ...m, content: m.content + '\n\n*(Generation stopped)*', isThinking: false }
            : m
        ));
      } else {
        console.error('CRM Chat error:', err);
        setMessages(prev => prev.map(m => 
          m.id === assistantMsgId 
            ? { ...m, content: `⚠️ Error contacting CRM Assistant: ${err.message || 'Please check that n8n and Ollama are reachable.'}`, isThinking: false }
            : m
        ));
      }
    } finally {
      setIsStreaming(false);
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

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-4xl mx-auto w-full bg-white dark:bg-charcoal-dark border-x border-neutral-200 dark:border-neutral-800 shadow-xl transition-colors">
      
      {/* Top Assistant Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/80 dark:bg-charcoal/80 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-md">
              <Bot className="w-5 h-5" />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 border-2 border-white dark:border-charcoal-dark rounded-full" title="Connected to Relaticle CRM" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">
                Relaticle CRM Assistant
              </h2>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold bg-cyan-100 dark:bg-cyan-950/60 text-cyan-800 dark:text-cyan-300 rounded border border-cyan-300 dark:border-cyan-800">
                crm-qwen:3b
              </span>
            </div>
            <p className="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
              <span className="inline-flex items-center gap-1">
                <Database className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                Relaticle CRM Active
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1">
                <Cpu className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                Ollama Local
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {onBackToCheckIn && (
            <button
              type="button"
              onClick={onBackToCheckIn}
              className="p-2 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-800 rounded-lg transition-colors text-xs flex items-center gap-1.5 font-medium border border-neutral-300 dark:border-neutral-700 mr-1"
              title="Return to Open House Check-In"
            >
              <ClipboardList className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="hidden sm:inline">Check-In</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setShowPrompts(prev => !prev)}
            className={`p-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              showPrompts 
                ? 'bg-neutral-200 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200' 
                : 'text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800'
            }`}
            title="Toggle suggested prompts"
          >
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span className="hidden sm:inline">Suggestions</span>
          </button>
          
          <button
            type="button"
            onClick={handleClearHistory}
            className="p-2 text-neutral-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors text-xs flex items-center gap-1"
            title="Clear conversation"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Clear</span>
          </button>
        </div>
      </div>

      {/* Suggested Prompts Drawer */}
      {showPrompts && (
        <div className="px-4 py-2.5 bg-neutral-100/70 dark:bg-charcoal/50 border-b border-neutral-200 dark:border-neutral-800 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400 whitespace-nowrap">
            Quick Actions:
          </span>
          <div className="flex items-center gap-2">
            {SUGGESTED_PROMPTS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(item.prompt)}
                disabled={isStreaming}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-white dark:bg-charcoal border border-neutral-200 dark:border-neutral-700 hover:border-cyan-500 dark:hover:border-cyan-400 text-neutral-700 dark:text-neutral-300 text-[11px] font-medium transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50"
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
          return (
            <div
              key={m.id}
              className={`flex gap-3 sm:gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-600 to-blue-700 text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[85%] sm:max-w-[75%]`}>
                <div
                  className={`p-3.5 sm:p-4 rounded-2xl text-xs sm:text-sm font-sans relative group ${
                    isUser
                      ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 rounded-br-none shadow-md'
                      : 'bg-neutral-100 dark:bg-neutral-800/80 text-neutral-900 dark:text-neutral-100 border border-neutral-200 dark:border-neutral-700/60 rounded-bl-none shadow-sm'
                  }`}
                >
                  {m.isThinking && !m.content ? (
                    <div className="flex items-center gap-2 py-1 text-neutral-500 dark:text-neutral-400 text-xs">
                      <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                      <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse delay-75" />
                      <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse delay-150" />
                      <span className="font-medium ml-1">Consulting Relaticle CRM...</span>
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
                  <span className="text-[10px] text-neutral-400 font-mono">
                    {m.timestamp}
                  </span>
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
              placeholder="Ask CRM assistant (e.g. Search for Surbhi, update phone, list tasks...)"
              className="w-full bg-white dark:bg-charcoal border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 text-xs sm:text-sm text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 resize-none shadow-sm transition-all"
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
          </div>

          {isStreaming ? (
            <button
              type="button"
              onClick={handleStop}
              className="h-11 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-md flex-shrink-0"
              title="Stop generation"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span className="hidden sm:inline">Stop</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="h-11 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 text-white font-bold text-xs flex items-center gap-1.5 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Send</span>
            </button>
          )}
        </form>

        <p className="text-[10px] text-neutral-400 text-center mt-2 font-sans">
          Responses are generated live via Ollama <code className="font-mono">crm-qwen:3b</code> and execute tool calls in Relaticle CRM.
        </p>
      </div>

    </div>
  );
}
