import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Clock, TrendingUp, Home } from 'lucide-react';
import ContactSection from '../components/ContactSection';
import FAQSection from '../components/FAQSection';
import { CITY_PAGES_DATA } from '../data/cityPagesData';

export default function CityMarketPage({ citySlug }) {
  const data = CITY_PAGES_DATA[citySlug];
  if (!data) return null;

  const routePath = `/cities/${data.slug}`;

  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      {/* Hero */}
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img
            src={data.heroImage}
            alt={`${data.city}, WA Real Estate Market`}
            className="w-full h-full object-cover opacity-20 grayscale"
          />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <Link
            to={data.parentMarketLink}
            className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-silver-dark hover:text-ivory font-bold mb-4 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>{data.parentMarketName}</span>
          </Link>
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-3 block">
            {data.regionTag}
          </span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">
            {data.city}, WA Real Estate
          </h1>
          <p className="text-silver-dark font-sans text-base md:text-lg max-w-2xl mx-auto">
            Data-driven home buying, strategic listing representation, and micro-market analytics in {data.city} ({data.county}) with Lokesh &ldquo;Loki&rdquo; Chanana.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          {/* Left Narrative */}
          <div className="lg:col-span-7 font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-6">
            <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-4">
              {data.city} Housing Market Intelligence
            </h2>
            {data.overview.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}

            {/* Key Neighborhoods */}
            <div className="pt-6">
              <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-4 flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                <span>Key {data.city} Neighborhoods &amp; Corridors</span>
              </h3>
              <div className="flex flex-wrap gap-2.5">
                {data.neighborhoods.map((hood) => (
                  <span
                    key={hood}
                    className="px-3.5 py-1.5 bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/20 text-xs font-semibold text-charcoal dark:text-silver rounded-sm"
                  >
                    {hood}
                  </span>
                ))}
              </div>
            </div>

            {/* Commute & Employment */}
            <div className="p-6 bg-white dark:bg-charcoal-dark border border-silver/30 dark:border-silver/20 mt-6">
              <h3 className="text-sm uppercase tracking-widest font-bold text-charcoal dark:text-silver mb-2 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Transit, Commute &amp; Economic Anchors</span>
              </h3>
              <p className="text-sm text-charcoal-light dark:text-silver-dark">
                {data.commuteHighlights}
              </p>
            </div>
          </div>

          {/* Right Analytics Card */}
          <div className="lg:col-span-5 space-y-8">
            <div className="p-8 bg-white dark:bg-charcoal-dark border border-silver/30 shadow-lg">
              <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold block mb-2">
                NWMLS Micro-Market Snapshot
              </span>
              <h3 className="text-2xl font-serif font-bold text-charcoal dark:text-silver mb-6">
                {data.city} Metrics
              </h3>
              <div className="grid grid-cols-2 gap-6 pb-6 border-b border-silver/20">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> Avg Target Price
                  </p>
                  <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">
                    {data.avgPrice}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1 flex items-center gap-1">
                    <Home className="w-3 h-3" /> Days on Market
                  </p>
                  <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">
                    {data.avgDom}
                  </p>
                </div>
              </div>
              <p className="text-xs text-silver-dark mt-4 italic">
                Want a custom Comparative Market Analysis (CMA) or off-market property alert for {data.city}? Reach out to Loki below.
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-3">
                <a
                  href="#contact"
                  className="flex-1 text-center bg-charcoal text-ivory dark:bg-silver dark:text-charcoal py-3 px-4 text-xs font-bold uppercase tracking-widest hover:opacity-90 transition-opacity"
                >
                  Request {data.city} CMA
                </a>
                <Link
                  to="/buyers"
                  className="flex-1 text-center border border-charcoal dark:border-silver text-charcoal dark:text-silver py-3 px-4 text-xs font-bold uppercase tracking-widest hover:bg-charcoal hover:text-ivory dark:hover:bg-silver dark:hover:text-charcoal transition-colors"
                >
                  Buyer&rsquo;s Guide
                </Link>
              </div>
            </div>

            <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-white dark:bg-charcoal-dark p-2 shadow-xl rounded-xl h-72 overflow-hidden">
              <img
                src={data.mapImage}
                alt={`Map of ${data.city}, ${data.county}`}
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>
      </div>

      <FAQSection
        routePath={routePath}
        heading={`${data.city}, WA Real Estate FAQ`}
        subheading={`Common questions about buying, selling, and investing in ${data.city}, ${data.county}.`}
      />
      <ContactSection />
    </div>
  );
}
