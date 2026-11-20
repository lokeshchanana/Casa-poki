import React, { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2,
  XCircle,
  Edit3,
  Sparkles,
  Image as ImageIcon,
  Video,
  BarChart3,
  CalendarClock,
  RefreshCw,
  Upload,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Send,
} from 'lucide-react';

const PLATFORM_LABELS = {
  instagram_carousel: 'IG Carousel (4:5)',
  instagram_post: 'IG Feed Post (4:5)',
  instagram_reel: 'IG Reel (9:16 MP4)',
  instagram_story: 'IG Story (9:16)',
  facebook: 'Facebook Post (1.91:1)',
  tiktok: 'TikTok Video (9:16 MP4)',
  twitter: 'X / Twitter (16:9)',
};

const mediaUrl = (path) => `/api/manager/social/media-file?path=${encodeURIComponent(path)}`;

export default function SocialStudio() {
  const [subTab, setSubTab] = useState('queue'); // 'queue' | 'create' | 'media' | 'cadence'
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [statusFilter, setStatusFilter] = useState('PENDING_APPROVAL');
  const [editingCaptions, setEditingCaptions] = useState({});
  const [slideIdx, setSlideIdx] = useState({});
  const [toast, setToast] = useState(null);

  // Create form state
  const [form, setForm] = useState({
    platform: 'instagram_carousel',
    visual_mode: 'animated_avatar',
    pillar: 'market_update',
    kicker: 'WA MARKET PULSE',
    title: 'What $750k Buys in Greater Seattle Right Now',
    subheadline: 'King & Pierce County Weekly Snapshot',
    caption: '',
    script_text: '',
    asset_id: '',
  });
  const [generating, setGenerating] = useState(false);

  const showToast = (msg, type = 'ok') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4500);
  };

  const fetchOverview = useCallback(async () => {
    try {
      const res = await fetch('/api/manager/social/overview');
      const data = await res.json();
      if (data.ok) setOverview(data);
    } catch (e) {
      showToast('Failed to load Social Studio data', 'err');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const handleApprove = async (post) => {
    setBusyId(post.id);
    try {
      const edited = editingCaptions[post.id];
      const res = await fetch(`/api/manager/social/posts/${post.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scheduled_for: post.scheduled_for,
          edited_caption: edited !== undefined ? edited : null,
        }),
      });
      const data = await res.json();
      if (data.ok) {
        showToast(
          data.dispatched_to === 'postiz'
            ? 'Approved & scheduled in Postiz!'
            : 'Approved locally (ready for Postiz once channel is paired).'
        );
        fetchOverview();
      } else {
        showToast(data.error || 'Approval failed', 'err');
      }
    } finally {
      setBusyId(null);
    }
  };

  const handleRevise = async (postId) => {
    const note = window.prompt('What should Maya & Leo change in this post?');
    if (!note) return;
    setBusyId(postId);
    try {
      await fetch(`/api/manager/social/posts/${postId}/revise`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ revision_notes: note }),
      });
      showToast('Sent back for revision.');
      fetchOverview();
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async (postId) => {
    setBusyId(postId);
    try {
      await fetch(`/api/manager/social/posts/${postId}/reject`, { method: 'POST' });
      showToast('Post rejected.');
      fetchOverview();
    } finally {
      setBusyId(null);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setGenerating(true);
    try {
      const res = await fetch('/api/manager/social/posts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, asset_id: form.asset_id || null }),
      });
      const data = await res.json();
      if (data.ok) {
        showToast('Draft rendered & added to Approval Queue!');
        setSubTab('queue');
        setStatusFilter('PENDING_APPROVAL');
        fetchOverview();
      } else {
        showToast(data.error || 'Generation failed', 'err');
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleUploadPhoto = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/manager/social/assets/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.ok) {
      showToast(`Uploaded ${data.asset.title}`);
      fetchOverview();
    } else {
      showToast(data.detail || 'Upload failed', 'err');
    }
  };

  const handleGooglePhotosPick = async () => {
    const gp = overview?.google_photos;
    if (!gp?.configured) {
      showToast('Add GOOGLE_PHOTOS_CLIENT_ID & SECRET in /tank/agents/.env first.', 'err');
      return;
    }
    if (!gp?.connected) {
      const r = await fetch('/api/manager/social/google-photos/auth-url');
      const d = await r.json();
      if (d.auth_url) window.open(d.auth_url, '_blank', 'width=520,height=680');
      showToast('Complete Google sign-in in the popup, then click Import again.');
      return;
    }
    const sr = await fetch('/api/manager/social/google-photos/session', { method: 'POST' });
    const sd = await sr.json();
    if (!sd.ok || !sd.picker_uri) {
      showToast(sd.error || 'Could not start Google Photos Picker', 'err');
      return;
    }
    window.open(sd.picker_uri, '_blank', 'width=900,height=720');
    showToast('Select your photos in Google Photos; syncing automatically...');
    const poll = setInterval(async () => {
      const pr = await fetch(`/api/manager/social/google-photos/session/${sd.session_id}`);
      const pd = await pr.json();
      if (pd.ready) {
        clearInterval(poll);
        showToast(`Imported ${pd.imported?.length || 0} Google Photos!`);
        fetchOverview();
      }
    }, 3000);
    setTimeout(() => clearInterval(poll), 180000);
  };

  const handleSyncAnalytics = async () => {
    setLoading(true);
    try {
      await fetch('/api/manager/social/analytics/sync', { method: 'POST' });
      showToast('Analytics synced & weekly cadence optimized!');
      fetchOverview();
    } finally {
      setLoading(false);
    }
  };

  const posts = (overview?.posts || []).filter((p) =>
    statusFilter === 'ALL' ? true : p.status === statusFilter
  );
  const pendingCount = (overview?.posts || []).filter((p) => p.status === 'PENDING_APPROVAL').length;
  const assets = overview?.assets || [];
  const avatars = assets.filter((a) => a.asset_type === 'avatar');
  const photos = assets.filter((a) => a.asset_type !== 'avatar');

  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 space-y-6">
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-4 py-3 rounded-xl shadow-lg text-xs font-bold border ${
            toast.type === 'err'
              ? 'bg-rose-600 text-white border-rose-500'
              : 'bg-charcoal text-ivory border-silver/30 dark:bg-silver dark:text-charcoal'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-charcoal-dark p-5 rounded-2xl border border-silver/30 dark:border-silver/20 border-l-4 border-l-charcoal dark:border-l-silver">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-500 dark:text-silver-dark">
            5-Agent Social Media Wing • Human-in-the-Loop Gate
          </p>
          <h2 className="text-2xl font-serif font-bold text-charcoal dark:text-silver mt-0.5">
            Social Media Studio & Approval Queue
          </h2>
          <p className="text-xs text-neutral-600 dark:text-silver-dark mt-1">
            Devon Brooks (Market/Trends) • Nadia Kapoor (Avatars/Photos) • Maya Reyes (Storyline) • Leo Bennett (Content) • Priya Nair (Cadence)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href="https://postiz.lokeshchanana.com"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold border border-charcoal/20 dark:border-silver/20 hover:bg-neutral-100 dark:hover:bg-charcoal transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open Postiz</span>
            <span
              className={`w-2 h-2 rounded-full ${
                overview?.postiz?.reachable ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </a>
          <button
            onClick={fetchOverview}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-charcoal text-ivory dark:bg-silver dark:text-charcoal"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Sub-Navigation */}
      <div className="flex flex-wrap gap-2">
        {[
          { id: 'queue', label: `Approval Queue (${pendingCount})`, icon: ShieldCheck },
          { id: 'create', label: 'Create & Research', icon: Sparkles },
          { id: 'media', label: `Avatars & Google Photos (${assets.length})`, icon: ImageIcon },
          { id: 'cadence', label: 'Analytics & Cadence', icon: BarChart3 },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setSubTab(id)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition border ${
              subTab === id
                ? 'bg-charcoal text-ivory border-charcoal dark:bg-silver dark:text-charcoal dark:border-silver shadow-sm'
                : 'bg-white dark:bg-charcoal-dark text-neutral-600 dark:text-silver-dark border-silver/30 dark:border-silver/20 hover:border-charcoal'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* TAB 1: APPROVAL QUEUE */}
      {subTab === 'queue' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {['PENDING_APPROVAL', 'APPROVED', 'SCHEDULED_POSTIZ', 'REVISION_REQUESTED', 'ALL'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wider border ${
                  statusFilter === st
                    ? 'bg-charcoal text-ivory dark:bg-silver dark:text-charcoal border-transparent'
                    : 'bg-white dark:bg-charcoal-dark text-neutral-500 border-silver/30'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>

          {posts.length === 0 ? (
            <div className="bg-white dark:bg-charcoal-dark p-10 rounded-2xl border border-silver/30 text-center space-y-3">
              <p className="text-sm font-serif font-bold text-charcoal dark:text-silver">
                No posts in {statusFilter.replace('_', ' ')}
              </p>
              <p className="text-xs text-neutral-500">
                Use "Create & Research" or ask Marcus Vance in the Manager tab to generate a campaign.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {posts.map((post) => {
                const media = post.media_paths || [];
                const curSlide = Math.min(slideIdx[post.id] || 0, Math.max(media.length - 1, 0));
                const activeFile = media[curSlide];
                const isVideo = activeFile && activeFile.endsWith('.mp4');
                const comp = post.compliance || {};

                return (
                  <div
                    key={post.id}
                    className="bg-white dark:bg-charcoal-dark rounded-2xl border border-silver/30 dark:border-silver/20 overflow-hidden flex flex-col"
                  >
                    <div className="p-4 border-b border-silver/20 flex items-center justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-ivory dark:bg-charcoal border border-silver/30">
                          {PLATFORM_LABELS[post.platform] || post.platform}
                        </span>
                        <span className="ml-2 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                          {post.visual_mode === 'animated_avatar' ? '🎭 Animated Avatar' : '📸 Real Photo'}
                        </span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${
                          post.status === 'PENDING_APPROVAL'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                            : post.status === 'SCHEDULED_POSTIZ' || post.status === 'APPROVED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : 'bg-neutral-200 text-neutral-700'
                        }`}
                      >
                        {post.status}
                      </span>
                    </div>

                    {/* Media Preview */}
                    {activeFile && (
                      <div className="bg-ivory dark:bg-charcoal p-4 flex flex-col items-center">
                        {isVideo ? (
                          <video
                            src={mediaUrl(activeFile)}
                            controls
                            className="max-h-96 rounded-xl border border-silver/30 shadow-sm"
                          />
                        ) : (
                          <img
                            src={mediaUrl(activeFile)}
                            alt={post.title}
                            className="max-h-96 object-contain rounded-xl border border-silver/30 shadow-sm"
                          />
                        )}
                        {media.length > 1 && (
                          <div className="flex items-center gap-2 mt-3">
                            {media.map((_, idx) => (
                              <button
                                key={idx}
                                onClick={() => setSlideIdx((s) => ({ ...s, [post.id]: idx }))}
                                className={`px-2.5 py-1 rounded text-[11px] font-bold ${
                                  curSlide === idx
                                    ? 'bg-charcoal text-ivory dark:bg-silver dark:text-charcoal'
                                    : 'bg-white dark:bg-charcoal-dark border border-silver/30'
                                }`}
                              >
                                Slide {idx + 1}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Copy & Metadata */}
                    <div className="p-4 space-y-3 flex-1">
                      <h3 className="font-serif font-bold text-base text-charcoal dark:text-silver">
                        {post.title}
                      </h3>
                      <textarea
                        rows={4}
                        value={editingCaptions[post.id] ?? post.caption}
                        onChange={(e) =>
                          setEditingCaptions((prev) => ({ ...prev, [post.id]: e.target.value }))
                        }
                        className="w-full text-xs p-3 rounded-xl bg-ivory dark:bg-charcoal border border-silver/30 text-charcoal-light dark:text-silver focus:outline-none focus:border-charcoal"
                      />
                      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-neutral-500">
                        <span className="inline-flex items-center gap-1">
                          <CalendarClock className="w-3.5 h-3.5" />
                          Target: {post.scheduled_for || 'Next Optimal Slot'}
                        </span>
                        {comp.passed !== false ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                            <ShieldCheck className="w-3.5 h-3.5" /> WA Compliance & No-AI-Tells OK
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-600 font-semibold">
                            <AlertTriangle className="w-3.5 h-3.5" /> {(comp.issues || []).join('; ')}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    {post.status === 'PENDING_APPROVAL' && (
                      <div className="p-4 border-t border-silver/20 flex flex-wrap gap-2">
                        <button
                          disabled={busyId === post.id}
                          onClick={() => handleApprove(post)}
                          className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Approve & Schedule</span>
                        </button>
                        <button
                          disabled={busyId === post.id}
                          onClick={() => handleRevise(post.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-bold border border-silver/40 hover:bg-neutral-100 dark:hover:bg-charcoal"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          <span>Revise</span>
                        </button>
                        <button
                          disabled={busyId === post.id}
                          onClick={() => handleReject(post.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-bold text-rose-600 border border-rose-200 hover:bg-rose-50 dark:border-rose-900/50"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CREATE & RESEARCH */}
      {subTab === 'create' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <form
            onSubmit={handleGenerate}
            className="bg-white dark:bg-charcoal-dark p-5 rounded-2xl border border-silver/30 space-y-4"
          >
            <h3 className="font-serif font-bold text-lg text-charcoal dark:text-silver">
              Quick Studio Generator (Maya + Leo)
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold uppercase mb-1">Platform & Format</label>
                <select
                  value={form.platform}
                  onChange={(e) => setForm({ ...form, platform: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-lg bg-ivory dark:bg-charcoal border border-silver/30"
                >
                  {Object.entries(PLATFORM_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold uppercase mb-1">Visual Mode</label>
                <select
                  value={form.visual_mode}
                  onChange={(e) => setForm({ ...form, visual_mode: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-lg bg-ivory dark:bg-charcoal border border-silver/30"
                >
                  <option value="animated_avatar">🎭 Animated Avatar (Loki)</option>
                  <option value="real_photo">📸 Real Photo (Google Photos)</option>
                  <option value="hybrid">✨ Hybrid (Photo BG + Avatar)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold uppercase mb-1">Kicker Badge</label>
                <input
                  value={form.kicker}
                  onChange={(e) => setForm({ ...form, kicker: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-lg bg-ivory dark:bg-charcoal border border-silver/30"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold uppercase mb-1">Select Avatar / Photo</label>
                <select
                  value={form.asset_id}
                  onChange={(e) => setForm({ ...form, asset_id: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-lg bg-ivory dark:bg-charcoal border border-silver/30"
                >
                  <option value="">Auto-select best match</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      [{a.asset_type}] {a.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase mb-1">Headline / Topic</label>
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="w-full text-xs p-2.5 rounded-lg bg-ivory dark:bg-charcoal border border-silver/30"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase mb-1">
                Voiceover Script / Storyline (optional override)
              </label>
              <textarea
                rows={3}
                value={form.script_text}
                onChange={(e) => setForm({ ...form, script_text: e.target.value })}
                placeholder="Leave blank for automatic PNW neighborly script..."
                className="w-full text-xs p-2.5 rounded-lg bg-ivory dark:bg-charcoal border border-silver/30"
              />
            </div>

            <button
              type="submit"
              disabled={generating}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-xs font-bold bg-charcoal text-ivory dark:bg-silver dark:text-charcoal disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{generating ? 'Rendering Asset & Audio...' : 'Render & Send to Approval Queue'}</span>
            </button>
          </form>

          {/* Devon Brooks Research Briefs */}
          <div className="bg-white dark:bg-charcoal-dark p-5 rounded-2xl border border-silver/30 space-y-3">
            <h3 className="font-serif font-bold text-lg text-charcoal dark:text-silver">
              Devon Brooks — WA Market & Viral Briefs
            </h3>
            <p className="text-xs text-neutral-500">
              Ask Marcus Vance in the Manager tab to run a fresh Greater Seattle market update or scout viral Reels formats anytime.
            </p>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {(overview?.briefs || []).length === 0 ? (
                <p className="text-xs text-neutral-400 italic">No research briefs saved yet.</p>
              ) : (
                overview.briefs.map((b) => (
                  <div key={b.id} className="p-3 rounded-xl bg-ivory dark:bg-charcoal border border-silver/30">
                    <div className="flex justify-between text-[10px] font-bold uppercase text-neutral-500">
                      <span>{b.brief_type} • {b.region}</span>
                      <span>{b.created_at?.slice(0, 10)}</span>
                    </div>
                    <p className="font-serif font-bold text-sm mt-1">{b.title}</p>
                    <p className="text-xs text-neutral-600 dark:text-silver-dark mt-1">{b.summary}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: AVATARS & GOOGLE PHOTOS */}
      {subTab === 'media' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-charcoal-dark p-5 rounded-2xl border border-silver/30 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="font-serif font-bold text-lg text-charcoal dark:text-silver">
                Nadia Kapoor — Animated Avatar Pack & Google Photos Library
              </h3>
              <p className="text-xs text-neutral-500 mt-0.5">
                Avatars are generated via Antigravity grounded on your likeness. Import real photos from Google Photos or upload directly.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleGooglePhotosPick}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-charcoal text-ivory dark:bg-silver dark:text-charcoal"
              >
                <ImageIcon className="w-4 h-4" />
                <span>Import from Google Photos</span>
              </button>
              <label className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border border-charcoal/30 dark:border-silver/30 cursor-pointer hover:bg-neutral-100 dark:hover:bg-charcoal">
                <Upload className="w-4 h-4" />
                <span>Upload Photo</span>
                <input type="file" accept="image/*" onChange={handleUploadPhoto} className="hidden" />
              </label>
            </div>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-3">
              Animated Avatar Pack ({avatars.length})
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {avatars.map((a) => (
                <div key={a.id} className="bg-white dark:bg-charcoal-dark rounded-xl border border-silver/30 overflow-hidden">
                  <img src={mediaUrl(a.file_path)} alt={a.title} className="w-full h-56 object-cover" />
                  <div className="p-3">
                    <p className="text-xs font-bold truncate">{a.title}</p>
                    <p className="text-[10px] text-neutral-500 mt-0.5">Used {a.usage_count}x</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-3">
              My Personal Photos ({photos.length})
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {photos.map((a) => (
                <div key={a.id} className="bg-white dark:bg-charcoal-dark rounded-xl border border-silver/30 overflow-hidden">
                  <img src={mediaUrl(a.file_path)} alt={a.title} className="w-full h-56 object-cover" />
                  <div className="p-3">
                    <p className="text-xs font-bold truncate">{a.title}</p>
                    <p className="text-[10px] text-neutral-500 mt-0.5">{a.source} • Used {a.usage_count}x</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ANALYTICS & CADENCE */}
      {subTab === 'cadence' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 bg-white dark:bg-charcoal-dark p-5 rounded-2xl border border-silver/30">
            <div>
              <h3 className="font-serif font-bold text-lg">Priya Nair — Analytics & Weekly Cadence</h3>
              <p className="text-xs text-neutral-500">
                Tracked Posts: {overview?.analytics?.total_tracked_posts || 0} • Postiz:{' '}
                {overview?.postiz?.api_key_configured ? 'Connected' : 'Ready for API Key'}
              </p>
            </div>
            <button
              onClick={handleSyncAnalytics}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-charcoal text-ivory dark:bg-silver dark:text-charcoal"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Sync Analytics & Optimize Cadence</span>
            </button>
          </div>

          <div className="bg-white dark:bg-charcoal-dark rounded-2xl border border-silver/30 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-ivory dark:bg-charcoal border-b border-silver/20 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Platform</th>
                  <th className="p-3.5">Day & Time (PT)</th>
                  <th className="p-3.5">Content Pillar</th>
                  <th className="p-3.5">Format</th>
                  <th className="p-3.5">Visual Mode</th>
                  <th className="p-3.5">Rationale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-silver/20">
                {(overview?.cadence || []).map((c) => (
                  <tr key={c.id}>
                    <td className="p-3.5 font-bold">{PLATFORM_LABELS[c.platform] || c.platform}</td>
                    <td className="p-3.5">{c.day_of_week} @ {c.time_pt} PT</td>
                    <td className="p-3.5">{c.pillar}</td>
                    <td className="p-3.5">{c.recommended_format}</td>
                    <td className="p-3.5">
                      {c.preferred_visual_mode === 'animated_avatar' ? '🎭 Animated Avatar' : c.preferred_visual_mode === 'real_photo' ? '📸 Real Photo' : '✨ Hybrid'}
                    </td>
                    <td className="p-3.5 text-neutral-500">{c.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
