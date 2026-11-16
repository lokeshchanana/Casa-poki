import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Play,
  MapPin,
  Volume2,
  VolumeX,
  X,
  Calendar,
} from 'lucide-react';
import { InstagramIcon } from './SocialLinks';

const FALLBACK_REELS = [
  {
    id: 'DfyItPpzpkP',
    url: 'https://www.instagram.com/reel/DfyItPpzpkP/',
    videoUrl: '/reels/DfyItPpzpkP.mp4',
    thumbnailUrl: '/reels/DfyItPpzpkP.jpg',
    title: 'Versatile Kent Home in West Hill North',
    location: 'Kent, WA',
    address: 'Kent, WA',
    specs: '3 Beds • 2.5 Baths • 2,484 Sq Ft',
    tag: 'Property Walkthrough',
    caption:
      'Step inside this versatile Kent home on a quiet dead-end street in West Hill North featuring 3 Beds, 2.5 Baths, 2,484 Sq. Ft., attached + detached 2-car garages, RV parking, and an expansive Trex deck.',
    author: 'lokeshchanana_re',
    date: 'Nov 15',
  },
  {
    id: 'DfvY0OkTI1h',
    url: 'https://www.instagram.com/reel/DfvY0OkTI1h/',
    videoUrl: '/reels/DfvY0OkTI1h.mp4',
    thumbnailUrl: '/reels/DfvY0OkTI1h.jpg',
    title: 'Remodeled North Seattle Retreat in Crown Hill',
    location: 'North Seattle, WA',
    address: 'Crown Hill / Blue Ridge, Seattle, WA',
    specs: '4 Beds • 3.5 Baths • 3,230 Sq Ft',
    tag: 'Property Walkthrough',
    caption:
      'Step inside this fully remodeled North Seattle retreat in the sought-after Crown Hill / Blue Ridge neighborhood with heated ensuite floors, private sauna, wet bar, and minutes from Carkeek Park.',
    author: 'lokeshchanana_re',
    date: 'Nov 14',
  },
  {
    id: 'Dfus7yoTkYl',
    url: 'https://www.instagram.com/reel/Dfus7yoTkYl/',
    videoUrl: '/reels/Dfus7yoTkYl.mp4',
    thumbnailUrl: '/reels/Dfus7yoTkYl.jpg',
    title: 'Highland Meadows Retreat on 0.34 Acres',
    location: 'Greater Seattle, WA',
    address: 'Highland Meadows, WA',
    specs: '5 Beds • 2.5 Baths • 2,620 Sq Ft',
    tag: 'Property Walkthrough',
    caption:
      'Touring this remodeled Highland Meadows retreat sitting on a private 0.34-acre cul-de-sac lot with floor-to-ceiling windows, vaulted ceilings, and a chef’s kitchen.',
    author: 'lokeshchanana_re',
    date: 'Nov 14',
  },
  {
    id: 'DffqxaXS5Gp',
    url: 'https://www.instagram.com/reel/DffqxaXS5Gp/',
    videoUrl: '/reels/DffqxaXS5Gp.mp4',
    thumbnailUrl: '/reels/DffqxaXS5Gp.jpg',
    title: 'Updated 4-Bedroom Residence in Maple Valley',
    location: 'Maple Valley, WA',
    address: 'Maple Valley, WA',
    specs: '4 Beds • 2.5 Baths • 2,380 Sq Ft',
    tag: 'Property Walkthrough',
    caption:
      'Step inside this 4-bedroom, 2.5-bath home offering 2,380 sq. ft. of thoughtfully updated living space in Maple Valley.',
    author: 'lokeshchanana_re',
    date: 'Nov 8',
  },
];

function ReelCard({ reel, onOpen }) {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [videoFailed, setVideoFailed] = useState(false);

  const handleMouseEnter = () => {
    if (videoFailed || !videoRef.current) return;
    const playPromise = videoRef.current.play();
    if (playPromise && typeof playPromise.then === 'function') {
      playPromise
        .then(() => setIsPlaying(true))
        .catch(() => {
          // Autoplay may be blocked by browser policy until interaction
        });
    }
  };

  const handleMouseLeave = () => {
    if (!videoRef.current) return;
    videoRef.current.pause();
    setIsPlaying(false);
  };

  const toggleMute = (e) => {
    e.stopPropagation();
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (videoRef.current) {
      videoRef.current.muted = nextMuted;
      if (!isPlaying) {
        videoRef.current
          .play()
          .then(() => setIsPlaying(true))
          .catch(() => {});
      }
    }
  };

  return (
    <article
      onClick={() => onOpen(reel)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen(reel);
        }
      }}
      aria-label={`Play property tour: ${reel.title} in ${reel.location}`}
      className="group relative aspect-[9/16] w-full rounded-xl overflow-hidden bg-charcoal-dark border border-silver/30 dark:border-silver/20 hover:border-charcoal dark:hover:border-silver shadow-lg hover:shadow-2xl transition-all duration-300 cursor-pointer select-none"
    >
      {/* Media Layer */}
      {!videoFailed && reel.videoUrl ? (
        <video
          ref={videoRef}
          src={reel.videoUrl}
          poster={reel.thumbnailUrl}
          muted={isMuted}
          loop
          playsInline
          preload="metadata"
          onError={() => setVideoFailed(true)}
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
        />
      ) : (
        <img
          src={reel.thumbnailUrl}
          alt={`${reel.title} — ${reel.location}`}
          loading="lazy"
          decoding="async"
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
        />
      )}

      {/* Subtle Top Vignette for Badges */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-[#151C23]/75 via-[#151C23]/25 to-transparent" />

      {/* Top Controls Row */}
      <div className="absolute top-3.5 inset-x-3.5 flex items-center justify-between gap-2 z-10">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#151C23]/75 backdrop-blur-md border border-silver/25 text-[10px] font-semibold tracking-wide text-ivory">
          <MapPin className="w-3 h-3 text-silver shrink-0" />
          <span className="truncate max-w-[140px]">{reel.location}</span>
        </span>

        {!videoFailed && reel.videoUrl && (
          <button
            type="button"
            onClick={toggleMute}
            aria-label={isMuted ? 'Unmute video preview' : 'Mute video preview'}
            className="p-2 rounded-full bg-[#151C23]/75 backdrop-blur-md border border-silver/25 text-ivory hover:bg-silver hover:text-charcoal transition-colors"
          >
            {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {/* Center Play Indicator (fades out while playing) */}
      <div
        className={`pointer-events-none absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${
          isPlaying ? 'opacity-0' : 'opacity-100'
        }`}
      >
        <div className="w-12 h-12 rounded-full bg-[#151C23]/65 backdrop-blur-md border border-silver/40 flex items-center justify-center text-ivory group-hover:scale-110 transition-transform duration-300 shadow-xl">
          <Play className="w-5 h-5 fill-ivory ml-0.5" />
        </div>
      </div>

      {/* Bottom Editorial Gradient & Left-Bar Info Overlay */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 pt-20 pb-4 px-4 bg-gradient-to-t from-[#151C23] via-[#151C23]/85 to-transparent">
        <div className="border-l-[3px] border-[#C0C0C0] pl-3 space-y-1">
          <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-[0.18em] text-silver">
            <span>{reel.tag || 'Property Tour'}</span>
            {reel.date && (
              <>
                <span className="opacity-40">•</span>
                <span>{reel.date}</span>
              </>
            )}
          </div>

          <h3 className="font-serif font-bold text-base text-ivory leading-snug line-clamp-2">
            {reel.title}
          </h3>

          {reel.specs && (
            <p className="text-[11px] font-sans text-silver/90 line-clamp-1 pt-0.5">
              {reel.specs}
            </p>
          )}
        </div>
      </div>
    </article>
  );
}

export default function InstagramReels({
  title = 'Property Walkthroughs & Market Reels',
  subtitle = 'Explore live Greater Seattle home tours, neighborhood insights, and new listings.',
}) {
  const [reels, setReels] = useState(FALLBACK_REELS);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [visibleCount, setVisibleCount] = useState(4);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const touchStartX = useRef(null);

  useEffect(() => {
    const updateVisibleCount = () => {
      if (window.innerWidth < 640) {
        setVisibleCount(1);
      } else if (window.innerWidth < 1024) {
        setVisibleCount(2);
      } else {
        setVisibleCount(4);
      }
    };
    updateVisibleCount();
    window.addEventListener('resize', updateVisibleCount);
    return () => window.removeEventListener('resize', updateVisibleCount);
  }, []);

  useEffect(() => {
    fetch('/instagram_reels.json?t=' + Date.now())
      .then((res) => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setReels(data.slice(0, 8));
        }
      })
      .catch(() => {
        // Fallback silently kept
      });
  }, []);

  // Clamp index if visibleCount changes
  const maxIndex = Math.max(0, reels.length - visibleCount);
  useEffect(() => {
    setCurrentIndex((prev) => Math.min(prev, maxIndex));
  }, [maxIndex]);

  // Keyboard navigation & scroll lock for lightbox modal
  useEffect(() => {
    if (selectedIndex === null) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSelectedIndex(null);
      } else if (e.key === 'ArrowRight') {
        setSelectedIndex((prev) => (prev !== null ? (prev + 1) % reels.length : null));
      } else if (e.key === 'ArrowLeft') {
        setSelectedIndex((prev) =>
          prev !== null ? (prev - 1 + reels.length) % reels.length : null
        );
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedIndex, reels.length]);

  const prevSlide = () => setCurrentIndex((prev) => Math.max(0, prev - 1));
  const nextSlide = () => setCurrentIndex((prev) => Math.min(maxIndex, prev + 1));

  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e) => {
    if (touchStartX.current === null) return;
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (diff > 50) nextSlide();
    else if (diff < -50) prevSlide();
    touchStartX.current = null;
  };

  const activeReel = selectedIndex !== null ? reels[selectedIndex] : null;

  const handleBookTour = () => {
    setSelectedIndex(null);
    const contactEl = document.getElementById('contact');
    if (contactEl) {
      contactEl.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section
      id="reels"
      className="py-20 bg-ivory dark:bg-charcoal transition-colors duration-300 relative border-b border-silver/20 overflow-hidden"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between mb-10 gap-6">
          <div className="space-y-3 max-w-2xl">
            <span className="inline-flex items-center gap-2 bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/20 px-3.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-charcoal dark:text-silver">
              <InstagramIcon className="w-3.5 h-3.5" />
              <span>Property Video Tours • @lokeshchanana_re</span>
            </span>

            <h2 className="text-3xl sm:text-4xl font-serif font-bold text-charcoal dark:text-silver">
              {title}
            </h2>

            <p className="text-charcoal-light dark:text-silver-dark text-sm sm:text-base font-sans">
              {subtitle}
            </p>
          </div>

          {/* Elfsight-style Profile Bar + Slider Controls */}
          <div className="flex flex-wrap items-center justify-between lg:justify-end gap-4 bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/20 px-4 py-2.5 rounded-xl shadow-sm">
            <div className="flex items-center gap-3">
              <img
                src="/loki-profile.jpg"
                alt="Lokesh Chanana"
                loading="lazy"
                decoding="async"
                className="w-9 h-9 rounded-full object-cover object-[50%_25%] border border-silver/60 scale-x-[-1]"
              />
              <div className="leading-tight">
                <p className="text-xs font-bold text-charcoal dark:text-silver">
                  @lokeshchanana_re
                </p>
                <p className="text-[10px] text-charcoal-light dark:text-silver-dark">
                  Real Broker LLC
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <a
                href="https://www.instagram.com/lokeshchanana_re"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-charcoal hover:bg-charcoal-light dark:bg-silver dark:hover:bg-white text-ivory dark:text-charcoal text-[10px] font-bold uppercase tracking-widest transition-colors"
              >
                <span>Follow</span>
                <ExternalLink className="w-3 h-3" />
              </a>

              {maxIndex > 0 && (
                <div className="flex items-center gap-1 pl-1 border-l border-silver/30 dark:border-silver/20">
                  <button
                    type="button"
                    onClick={prevSlide}
                    disabled={currentIndex === 0}
                    aria-label="Previous reels"
                    className={`p-2 rounded-md border border-silver/30 dark:border-silver/20 text-charcoal dark:text-silver transition-colors ${
                      currentIndex === 0
                        ? 'opacity-30 cursor-not-allowed'
                        : 'hover:bg-charcoal hover:text-ivory dark:hover:bg-silver dark:hover:text-charcoal'
                    }`}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={nextSlide}
                    disabled={currentIndex >= maxIndex}
                    aria-label="Next reels"
                    className={`p-2 rounded-md border border-silver/30 dark:border-silver/20 text-charcoal dark:text-silver transition-colors ${
                      currentIndex >= maxIndex
                        ? 'opacity-30 cursor-not-allowed'
                        : 'hover:bg-charcoal hover:text-ivory dark:hover:bg-silver dark:hover:text-charcoal'
                    }`}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 9:16 Video Carousel */}
        <div
          className="relative overflow-hidden"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <div
            className="flex transition-transform duration-500 ease-out gap-5"
            style={{
              transform: `translateX(calc(-${currentIndex * (100 / visibleCount)}% - ${
                currentIndex * (20 / visibleCount)
              }px))`,
            }}
          >
            {reels.map((reel, idx) => (
              <div
                key={reel.id}
                className="w-full sm:w-[calc(50%-10px)] lg:w-[calc(25%-15px)] shrink-0"
              >
                <ReelCard reel={reel} onOpen={() => setSelectedIndex(idx)} />
              </div>
            ))}
          </div>
        </div>

        {/* Pagination Dots */}
        {maxIndex > 0 && (
          <div className="flex items-center justify-center gap-2 mt-7">
            {Array.from({ length: maxIndex + 1 }).map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentIndex(idx)}
                aria-label={`Go to slide ${idx + 1}`}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  currentIndex === idx
                    ? 'w-8 bg-charcoal dark:bg-silver'
                    : 'w-2 bg-silver/50 dark:bg-silver/25 hover:bg-silver'
                }`}
              />
            ))}
          </div>
        )}

        {/* Signature Callout Banner */}
        <div className="mt-10 p-6 bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/20 border-l-4 border-l-charcoal dark:border-l-silver flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
          <div className="text-center sm:text-left">
            <h3 className="font-serif font-bold text-lg text-charcoal dark:text-silver">
              Want a private video tour of a specific home?
            </h3>
            <p className="text-xs sm:text-sm text-charcoal-light dark:text-silver-dark mt-0.5">
              Loki provides unedited, detailed walkthroughs for relocating buyers and busy locals across Greater Seattle.
            </p>
          </div>
          <a
            href="#contact"
            className="shrink-0 px-5 py-3 bg-charcoal hover:bg-charcoal-light dark:bg-silver dark:hover:bg-white text-ivory dark:text-charcoal text-xs font-bold uppercase tracking-widest transition-colors"
          >
            Request Private Walkthrough
          </a>
        </div>
      </div>

      {/* Cinema Lightbox Modal */}
      {activeReel && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={activeReel.title}
          onClick={() => setSelectedIndex(null)}
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-4xl bg-charcoal-dark border border-silver/25 rounded-2xl overflow-hidden shadow-2xl grid grid-cols-1 md:grid-cols-12 max-h-[90vh]"
          >
            {/* Close Button */}
            <button
              type="button"
              onClick={() => setSelectedIndex(null)}
              aria-label="Close video modal"
              className="absolute top-3 right-3 z-20 p-2 rounded-full bg-charcoal/80 border border-silver/30 text-ivory hover:bg-silver hover:text-charcoal transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Left: 9:16 Video Player */}
            <div className="md:col-span-6 bg-black flex items-center justify-center relative max-h-[60vh] md:max-h-[85vh]">
              {activeReel.videoUrl ? (
                <video
                  key={activeReel.id}
                  src={activeReel.videoUrl}
                  poster={activeReel.thumbnailUrl}
                  controls
                  autoPlay
                  loop
                  playsInline
                  className="w-full h-full max-h-[60vh] md:max-h-[85vh] object-contain"
                />
              ) : (
                <img
                  src={activeReel.thumbnailUrl}
                  alt={activeReel.title}
                  className="w-full h-full object-contain"
                />
              )}
            </div>

            {/* Right: Property Details & Actions */}
            <div className="md:col-span-6 p-6 sm:p-8 flex flex-col justify-between bg-charcoal-dark text-ivory overflow-y-auto">
              <div className="space-y-4">
                <div className="flex items-center gap-3 pb-4 border-b border-silver/15">
                  <img
                    src="/loki-profile.jpg"
                    alt="Lokesh Chanana"
                    className="w-10 h-10 rounded-full object-cover object-[50%_25%] border border-silver/50 scale-x-[-1]"
                  />
                  <div>
                    <p className="text-xs font-bold text-ivory">@lokeshchanana_re</p>
                    <p className="text-[10px] text-silver-dark">
                      Lokesh Chanana (Loki) • Real Broker LLC
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-silver">
                  <span className="px-2.5 py-1 border border-silver/25 bg-charcoal">
                    {activeReel.tag || 'Property Tour'}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 border border-silver/25 bg-charcoal">
                    <MapPin className="w-3 h-3" />
                    {activeReel.location}
                  </span>
                  {activeReel.date && (
                    <span className="text-silver-dark ml-1">{activeReel.date}</span>
                  )}
                </div>

                <h3 className="font-serif font-bold text-2xl text-ivory leading-snug">
                  {activeReel.title}
                </h3>

                {activeReel.specs && (
                  <p className="text-xs font-bold uppercase tracking-wider text-silver border-l-2 border-silver pl-3">
                    {activeReel.specs}
                  </p>
                )}

                {activeReel.caption && (
                  <p className="text-sm text-silver-dark leading-relaxed whitespace-pre-line max-h-48 overflow-y-auto pr-1">
                    {activeReel.caption}
                  </p>
                )}
              </div>

              <div className="pt-6 mt-6 border-t border-silver/15 space-y-3">
                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    type="button"
                    onClick={handleBookTour}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-silver hover:bg-white text-charcoal text-xs font-bold uppercase tracking-widest transition-colors"
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Schedule Private Tour</span>
                  </button>

                  <a
                    href={activeReel.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-2 px-4 py-3 border border-silver/40 hover:border-silver text-ivory text-xs font-bold uppercase tracking-widest transition-colors"
                  >
                    <span>Instagram</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>

                {reels.length > 1 && (
                  <div className="flex items-center justify-between pt-2 text-[11px] text-silver-dark">
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedIndex((selectedIndex - 1 + reels.length) % reels.length)
                      }
                      className="inline-flex items-center gap-1 hover:text-ivory transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      <span>Previous Tour</span>
                    </button>
                    <span>
                      {selectedIndex + 1} / {reels.length}
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedIndex((selectedIndex + 1) % reels.length)}
                      className="inline-flex items-center gap-1 hover:text-ivory transition-colors"
                    >
                      <span>Next Tour</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
