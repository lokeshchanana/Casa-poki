
import React from 'react';
import ContactSection from '../components/ContactSection';
import FAQSection from '../components/FAQSection';

export default function InvestorsGuide() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="https://images.unsplash.com/photo-1460472178825-e5240623afd5?auto=format&fit=crop&w=2000&q=80" alt="Real Estate Investing" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">The Ultimate Guide</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Real Estate Investment</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Calculating ARV, Cap Rates, and sourcing high-yield acquisitions in the Pacific Northwest.</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-20 font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-16">
        
        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">1. Sourcing the Right Asset</h2>
          <p className="mb-4">In a high-appreciation market like Seattle, cash-flow positive properties on the MLS are exceedingly rare. Finding value requires identifying distressed assets, off-market opportunities, or properties with untapped zoning potential (e.g., DADU/AADU additions).</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">2. Calculating ARV (After Repair Value)</h2>
          <p className="mb-4">The golden rule of flipping or BRRRR (Buy, Rehab, Rent, Refinance, Repeat) is accuracy in the ARV. I utilize highly specific localized comp data to project the future value of an asset post-renovation. We do not speculate; we rely on data.</p>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">3. Capital Expenditure (CapEx) Evaluation</h2>
          <p className="mb-4">Overestimating ARV or underestimating CapEx is how investors lose money. I help connect you with trusted local contractors to evaluate:</p>
          <ul className="list-disc pl-5 space-y-2">
            <li>Foundation and structural integrity.</li>
            <li>Roof, Plumbing, and Electrical overhaul costs.</li>
            <li>Permitting timelines within specific municipalities (Seattle vs. Shoreline vs. Bellevue).</li>
          </ul>
        </section>

        <section>
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-6">4. Cap Rates & Cash-on-Cash Return</h2>
          <p>For buy-and-hold investors, we run deep cash flow analyses. We factor in property management fees, vacancy rates, maintenance reserves, and property tax reassessments to ensure the math aligns with your portfolio yield requirements.</p>
        </section>
      </div>

      <FAQSection routePath="/investors" heading="Pacific Northwest Real Estate Investment FAQ" />
      <ContactSection />
    </div>
  );
}
