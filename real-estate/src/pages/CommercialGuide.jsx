
import React from 'react';
import ContactSection from '../components/ContactSection';
import FAQSection from '../components/FAQSection';

export default function CommercialGuide() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=2000&q=80" alt="Commercial Real Estate" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">The Ultimate Guide</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Commercial Acquisitions</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Navigating zoning, feasibility, and complex transactions for owner-users and institutional investors.</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-20 font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-16">
        
        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">1. Needs Analysis & Site Selection</h2>
          <p className="mb-4">Whether you are expanding a retail footprint, seeking industrial warehouse space, or acquiring a multi-family apartment building, site selection is critical. We analyze traffic counts, demographic shifts, and logistics corridors.</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">2. Zoning & Feasibility</h2>
          <p className="mb-4">A property is only as valuable as what the municipality allows you to do with it. We conduct rigorous feasibility studies during the due diligence phase, reviewing highest and best use, parking requirements, and environmental (Phase I/II) constraints.</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">3. Lease vs. Buy Analysis</h2>
          <p className="mb-4">For business owners, tying up capital in real estate is a major decision. We run comparative financial models analyzing the tax benefits of depreciation and asset appreciation versus the liquidity and flexibility of leasing.</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">4. 1031 Exchanges</h2>
          <p>Deferring capital gains tax is a primary vehicle for wealth generation in real estate. We specialize in coordinating 1031 exchanges, adhering to the strict 45-day identification and 180-day closing timelines, and sourcing secure replacement properties.</p>
        </section>
      </div>

      <FAQSection routePath="/commercial" heading="Commercial Real Estate & 1031 Exchange FAQ" />
      <ContactSection />
    </div>
  );
}
