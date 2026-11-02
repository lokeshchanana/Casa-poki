
import React from 'react';
import ContactSection from '../components/ContactSection';
import FAQSection from '../components/FAQSection';
import ValuationCards from '../components/ValuationCards';

export default function SellersGuide() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="https://images.unsplash.com/photo-1582407947304-fd86f028f716?auto=format&fit=crop&w=2000&q=80" alt="Selling in Seattle" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">The Ultimate Guide</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Selling Your Seattle Home</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Maximizing your asset's return through data-driven pricing, strategic preparation, and aggressive omnichannel marketing.</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-20 font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-16">
        
        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">1. The Analytical Pricing Strategy</h2>
          <p className="mb-4">Pricing a home is not a guessing game; it is an economic model. We don't just look at what sold in your neighborhood last month. We look at active inventory absorption rates, interest rate macro-trends, and the micro-market Days on Market (DOM) velocity.</p>
          <p>By positioning your home perfectly within the pricing matrix, we generate maximum initial velocity, which frequently results in multiple-offer scenarios.</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">2. Asset Preparation & ROI</h2>
          <p className="mb-4">Not all renovations yield a positive return. Before you spend a dime, I will audit your property to identify high-ROI improvements.</p>
          <ul className="list-disc pl-5 space-y-2">
            <li><strong>Paint & Flooring:</strong> Often yields a 200%+ ROI.</li>
            <li><strong>Professional Staging:</strong> Vacant homes sit; staged homes sell. Staging provides scale and emotional resonance to buyers.</li>
            <li><strong>Pre-Inspections:</strong> By providing a clean inspection report upfront, we remove the buyer's biggest contingency and fear.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">3. Omnichannel Digital Marketing</h2>
          <p className="mb-4">Placing a sign in the yard and listing on the MLS is the bare minimum. My marketing protocol involves:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <div className="bg-white dark:bg-charcoal-dark p-6 border border-silver/30">
              <h3 className="font-bold text-charcoal dark:text-silver mb-2">Visual Media</h3>
              <p className="text-sm">Twilight photography, 3D Matterport tours, and cinematic drone video to capture out-of-state tech buyers.</p>
            </div>
            <div className="bg-white dark:bg-charcoal-dark p-6 border border-silver/30">
              <h3 className="font-bold text-charcoal dark:text-silver mb-2">Targeted Distribution</h3>
              <p className="text-sm">Paid social media campaigns geofenced to high-intent buyer demographics and syndicated globally.</p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">4. Offer Review & Negotiation</h2>
          <p>When offers arrive, I compile them into a clear analytical matrix. We will evaluate not just the top-line price, but the strength of the financing, the earnest money release terms, and the closing timeline to select the offer with the highest probability of a seamless close.</p>
        </section>
      </div>

      <ValuationCards />
      <FAQSection routePath="/sellers" heading="Home Seller Pricing & Marketing FAQ" />
      <ContactSection />
    </div>
  );
}
