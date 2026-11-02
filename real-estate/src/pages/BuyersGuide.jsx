
import React from 'react';
import ContactSection from '../components/ContactSection';
import FAQSection from '../components/FAQSection';
import MortgageCalculator from '../components/MortgageCalculator';

export default function BuyersGuide() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      {/* Hero */}
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=2000&q=80" alt="Buying in Seattle" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">The Ultimate Guide</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Buying a Home in Seattle</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Navigating the Greater Seattle housing market requires strategic precision, deep micro-market intelligence, and an agent who fiercely protects your interests.</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-20 font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-16">
        
        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">1. Initial Consultation & Market Analytics</h2>
          <p className="mb-4">We begin by aligning on your lifestyle goals, financial parameters, and investment timeline. This isn't just about finding a house with the right number of bedrooms; it's about evaluating the long-term viability of the asset.</p>
          <ul className="list-disc pl-5 space-y-2">
            <li>Reviewing active macro-economic trends in King and Snohomish counties.</li>
            <li>Analyzing neighborhood-specific appreciation rates.</li>
            <li>Defining your non-negotiables vs. flexible criteria.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">2. Pre-Approval & Financial Strategy</h2>
          <p className="mb-4">In a competitive market like Seattle, your pre-approval letter is just as important as your offer price. I work with a network of elite local lenders who understand the nuances of jumbo loans, tech-RSU income, and bridge financing.</p>
          <div className="bg-white dark:bg-charcoal-dark p-6 border border-silver/30 border-l-4 border-l-charcoal dark:border-l-silver my-6">
            <h3 className="font-bold text-charcoal dark:text-silver mb-2">Why Local Lenders Matter</h3>
            <p className="text-sm">Listing agents often prefer buyers working with reputable local lenders because they are known to close on time and have direct lines of communication, unlike large national banks.</p>
          </div>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">3. Targeted Property Search & Tours</h2>
          <p className="mb-4">Once we have our criteria, the hunt begins. I leverage the NWMLS RESO Web API, off-market networks, and my relationships within REAL Broker LLC and the Lakhani Team to find inventory before it hits the mainstream portals.</p>
          <p>During tours, my role transitions to an analyst and inspector. I am looking for foundation issues, age of major systems (roof, HVAC), and potential zoning restrictions for future developments.</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">4. Offer Engineering</h2>
          <p className="mb-4">Writing a winning offer is a science. It's rarely just about the highest price. We will look at the Seller's timeline, the listing agent's tendencies, and craft a data-backed offer.</p>
          <ul className="list-disc pl-5 space-y-2">
            <li><strong>Escalation Clauses:</strong> Using intelligent caps to win without overpaying.</li>
            <li><strong>Earnest Money:</strong> Structuring deposits to show immense strength.</li>
            <li><strong>Inspection Strategies:</strong> Utilizing pre-inspections to waive contingencies safely.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">5. Due Diligence to Closing</h2>
          <p>Once mutually accepted, my operations team takes over the timeline. We coordinate with escrow, title, and the lender to ensure a frictionless closing process. I remain at the center of all negotiations should any appraisal or inspection hurdles arise.</p>
        </section>
      </div>

      <MortgageCalculator />
      <FAQSection routePath="/buyers" heading="Seattle & Eastside Home Buyer FAQ" />
      <ContactSection />
    </div>
  );
}
