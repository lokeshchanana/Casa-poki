import React, { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, ExternalLink, Play, MapPin, Sparkles, Video } from 'lucide-react';
import { InstagramIcon } from './SocialLinks';

const FALLBACK_REELS = [
  {
    id: "DefBayDkggh",
    url: "https://www.instagram.com/reel/DefBayDkggh/",
    title: "Move-In Ready Single-Level Home",
    location: "Fife, WA",
    address: "6304 Sheffield Ln E, Fife, WA 98424",
    specs: "3 Beds • 2 Baths • 1,614 Sq Ft",
    tag: "Gated 55+ Community Tour",
    author: "lokeshchanana_re"
  },
  {
    id: "DeNfft0EdO0",
    url: "https://www.instagram.com/reel/DeNfft0EdO0/",
    title: "Haller Lake Modern Retreat",
    location: "North Seattle, WA",
    address: "Haller Lake, Seattle, WA",
    specs: "4 Beds • 2.5 Baths • 2,751 Sq Ft",
    tag: "Modern Home Tour",
    author: "lokeshchanana_re"
  },
  {
    id: "DdxZw6Ozj4t",
    url: "https://www.instagram.com/reel/DdxZw6Ozj4t/",
    title: "Turnkey Multi-Gen Seattle Residence",
    location: "Seattle, WA",
    address: "10036 1st Ave S, Seattle, WA 98168",
    specs: "4 Beds • 2 Baths • 1,760 Sq Ft",
    tag: "Property Walkthrough",
    author: "lokeshchanana_re"
  }
];

export default function InstagramReels({ title = "Latest Property Tours & Reels", subtitle = "Explore live property walkthroughs, open houses, and market insights across Greater Seattle." }) {
  const [reels, setReels] = useState(FALLBACK_REELS);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [activeEmbeds, setActiveEmbeds] = useState({});
  const [visibleCount, setVisibleCount] = useState(3);
  const touchStartX = useRef(null);

  // Responsive items count per view
  useEffect(() => {
    const updateVisibleCount = () => {
      if (window.innerWidth < 640) {
        setVisibleCount(1);
      } else if (window.innerWidth < 1024) {
        setVisibleCount(2);
      } else {
        setVisibleCount(3);
      }
    };
    updateVisibleCount();
    window.addEventListener('resize', updateVisibleCount);
    return () => window.removeEventListener('resize', updateVisibleCount);
  }, []);

  // Fetch dynamic reels JSON if available
  useEffect(() => {
    fetch('/instagram_reels.json?t=' + Date.now())
      .then((res) => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setReels(data.slice(0, 6));
        }
      })
      .catch(() => {
        // Fallback silently kept
      });
  }, []);

  const maxIndex = Math.max(0, reels.length - visibleCount);

  const prevSlide = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const nextSlide = () => {
    setCurrentIndex((prev) => Math.min(maxIndex, prev + 1));
  };

  const toggleEmbed = (id) => {
    setActiveEmbeds((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Touch swipe support for mobile
  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e) => {
    if (touchStartX.current === null) return;
    const touchEndX = e.changedTouches[0].clientX;
    const diff = touchStartX.current - touchEndX;
    if (diff > 50) {
      nextSlide();
    } else if (diff < -50) {
      prevSlide();
    }
    touchStartX.current = null;
  };

  return (
    <section id="reels" className="py-20 bg-ivory/60 dark:bg-charcoal/60 transition-colors duration-300 relative border-b border-silver/20 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Header with Title and Instagram Follow Action */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-gradient-to-r from-[#833AB4]/10 via-[#FD1D1D]/10 to-[#F77737]/10 dark:from-[#833AB4]/20 dark:to-[#F77737]/20 border border-[#E4405F]/30 px-3.5 py-1 rounded-full text-[#E4405F] dark:text-[#F77737] text-xs font-bold uppercase tracking-wider">
              <InstagramIcon className="w-3.5 h-3.5" />
              <span>Instagram Video Showcase</span>
            </div>
            
            <h2 className="text-3xl sm:text-4xl font-serif font-bold text-charcoal dark:text-silver">
              {title}
            </h2>
            
            <p className="text-charcoal-light dark:text-silver-dark text-sm sm:text-base font-sans">
              {subtitle}
            </p>
          </div>

          {/* Controls & Follow CTA */}
          <div className="flex flex-wrap items-center gap-3">
            <a
              href="https://www.instagram.com/lokeshchanana_re"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-gradient-to-r from-[#833AB4] via-[#FD1D1D] to-[#F77737] text-white text-xs font-bold uppercase tracking-widest shadow-md hover:opacity-90 transition-opacity"
            >
              <InstagramIcon className="w-4 h-4" />
              <span>Follow @lokeshchanana_re</span>
              <ExternalLink className="w-3 h-3" />
            </a>

            {/* Slider Navigation Buttons */}
            {maxIndex > 0 && (
              <div className="flex items-center gap-1.5 ml-2">
                <button
                  type="button"
                  onClick={prevSlide}
                  disabled={currentIndex === 0}
                  aria-label="Previous reels"
                  className={`p-2.5 rounded-md border border-silver/40 dark:border-silver/20 text-charcoal dark:text-silver transition-colors ${
                    currentIndex === 0 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-silver/20 dark:hover:bg-silver/10'
                  }`}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                
                <button
                  type="button"
                  onClick={nextSlide}
                  disabled={currentIndex >= maxIndex}
                  aria-label="Next reels"
                  className={`p-2.5 rounded-md border border-silver/40 dark:border-silver/20 text-charcoal dark:text-silver transition-colors ${
                    currentIndex >= maxIndex ? 'opacity-30 cursor-not-allowed' : 'hover:bg-silver/20 dark:hover:bg-silver/10'
                  }`}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Carousel Container */}
        <div 
          className="relative overflow-hidden"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <div
            className="flex transition-transform duration-500 ease-out gap-6"
            style={{
              transform: `translateX(-${currentIndex * (100 / visibleCount)}%)`,
            }}
          >
            {reels.map((reel, index) => {
              const isEmbedActive = activeEmbeds[reel.id] !== false; // Active by default or toggled
              return (
                <div
                  key={reel.id}
                  className="w-full sm:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)] shrink-0 flex flex-col"
                >
                  <div className="bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/15 rounded-2xl overflow-hidden shadow-lg hover:border-silver/60 dark:hover:border-silver/30 transition-all flex flex-col h-full group">
                    
                    {/* Top Metadata Header */}
                    <div className="p-3.5 border-b border-silver/20 flex items-center justify-between bg-ivory/50 dark:bg-charcoal/50">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-full bg-[#E4405F]/10 text-[#E4405F] dark:text-[#F77737]">
                          <InstagramIcon className="w-3.5 h-3.5" />
                        </span>
                        <div>
                          <p className="text-[10px] uppercase font-bold tracking-wider text-charcoal dark:text-silver">
                            @{reel.author || 'lokeshchanana_re'}
                          </p>
                          <p className="text-[9px] text-silver-dark font-sans flex items-center gap-1">
                            <MapPin className="w-2.5 h-2.5 text-cyan-700 dark:text-cyan-400" />
                            <span>{reel.location}</span>
                          </p>
                        </div>
                      </div>

                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-silver/15 text-charcoal-light dark:text-silver-dark">
                        Reel #{index + 1}
                      </span>
                    </div>

                    {/* Reel Video Frame */}
                    <div className="relative bg-black flex-1 min-h-[460px] sm:min-h-[480px] overflow-hidden flex items-center justify-center">
                      <iframe
                        src={`https://www.instagram.com/reel/${reel.id}/embed/`}
                        className="w-full h-[470px] border-0"
                        title={reel.title}
                        allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                        allowFullScreen
                        loading="lazy"
                      />
                    </div>

                    {/* Card Footer with Property Context & Direct CTA */}
                    <div className="p-4 bg-white dark:bg-charcoal-dark border-t border-silver/20 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[9px] uppercase font-bold tracking-widest text-[#E4405F] dark:text-[#F77737] block">
                            {reel.tag || 'Property Tour'}
                          </span>
                          <h3 className="font-serif font-bold text-sm text-charcoal dark:text-silver leading-snug line-clamp-1">
                            {reel.title}
                          </h3>
                        </div>
                      </div>

                      {reel.specs && (
                        <p className="text-[11px] text-charcoal-light dark:text-silver-dark font-medium line-clamp-1">
                          {reel.specs}
                        </p>
                      )}

                      <div className="pt-2 flex items-center justify-between border-t border-silver/15">
                        <a
                          href={reel.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-bold text-charcoal hover:text-[#E4405F] dark:text-silver dark:hover:text-[#F77737] transition-colors"
                        >
                          <span>Open on Instagram</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>

                        <a
                          href="#contact"
                          className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded border border-silver/30 dark:border-silver/20 text-charcoal dark:text-silver hover:bg-charcoal hover:text-white dark:hover:bg-silver dark:hover:text-charcoal transition-colors"
                        >
                          Tour With Loki
                        </a>
                      </div>
                    </div>

                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Carousel Pagination Dots */}
        {maxIndex > 0 && (
          <div className="flex items-center justify-center gap-2 mt-8">
            {Array.from({ length: maxIndex + 1 }).map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setCurrentIndex(idx)}
                aria-label={`Go to slide ${idx + 1}`}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  currentIndex === idx
                    ? 'w-8 bg-[#E4405F] dark:bg-[#F77737]'
                    : 'w-2 bg-silver/40 dark:bg-silver/20 hover:bg-silver/60'
                }`}
              />
            ))}
          </div>
        )}

        {/* Bottom Banner for Direct Engagement */}
        <div className="mt-12 p-6 rounded-2xl bg-gradient-to-r from-silver/10 via-white to-silver/10 dark:from-charcoal-dark dark:via-charcoal dark:to-charcoal-dark border border-silver/30 dark:border-silver/15 text-center flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <h4 className="font-serif font-bold text-base text-charcoal dark:text-silver">
              Want a video tour of a specific home or neighborhood?
            </h4>
            <p className="text-xs text-charcoal-light dark:text-silver-dark mt-0.5">
              Loki provides bespoke video walkthroughs for out-of-state buyers and busy locals.
            </p>
          </div>
          <a
            href="#contact"
            className="shrink-0 px-5 py-2.5 rounded-md bg-charcoal text-ivory hover:bg-charcoal-light dark:bg-silver dark:text-charcoal dark:hover:bg-white text-xs font-bold uppercase tracking-widest transition-colors shadow"
          >
            Request Private Walkthrough
          </a>
        </div>

      </div>
    </section>
  );
}
