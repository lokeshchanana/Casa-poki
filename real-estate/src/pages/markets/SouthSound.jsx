
import React from 'react';
import ContactSection from '../../components/ContactSection';
import FAQSection from '../../components/FAQSection';

export default function MarketPage() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="/hero_south.jpg" alt="South Sound Hub" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">Market Profile: JBLM Defense & Value Baseline</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">South Sound Hub</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Cities: Tacoma, Gig Harbor, Puyallup, Lakewood, Spanaway</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          
          <div className="font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-6">
            <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-8">Regional Analysis</h2>
            
<div className="space-y-4">
  <p>The South Sound Hub, anchored by Pierce County cities including Tacoma, Gig Harbor, Puyallup, Lakewood, and Spanaway, provides an exceptional value baseline for the entire Puget Sound region. This dynamic market is heavily influenced by the massive economic footprint of Joint Base Lewis-McChord (JBLM), which guarantees a steady, reliable influx of military and defense-contractor personnel seeking housing.</p>
  <p>Tacoma, the gritty yet rapidly revitalizing anchor city, boasts historic architecture, a burgeoning arts district, and a deep-water port that drives industrial logistics. Just across the iconic Narrows Bridge, Gig Harbor offers a striking contrast with its affluent maritime lifestyle, luxury waterfront properties, and boutique harbor-front charm. Puyallup and Spanaway round out the region by offering substantial suburban developments and new construction at price points rarely seen further north.</p>
  <p>For investors, the South Sound is often considered the gold standard for cash-flowing rentals and BRRRR (Buy, Rehab, Rent, Refinance, Repeat) strategies. The lower barrier to entry, combined with relentless rental demand from JBLM and migrating Seattleites, creates a highly lucrative environment for strategic real estate acquisition.</p>
</div>

            
            <div className="mt-12 p-8 bg-white dark:bg-charcoal-dark border border-silver/30">
               <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-6">Current Analytics</h3>
               <div className="grid grid-cols-2 gap-6">
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Avg Target Price</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">$560K+</p>
                 </div>
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Days on Market</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">20 Days</p>
                 </div>
               </div>
               <p className="text-xs text-silver-dark mt-6 italic">*Aggregated from recent NWMLS and regional reports. Market velocities shift rapidly.</p>
            </div>
          </div>

          <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-white dark:bg-charcoal-dark p-2 shadow-2xl rounded-xl h-[400px] lg:h-[600px] overflow-hidden group">
             <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-charcoal/20 to-transparent"></div>
             <img src="/map_south.jpg" alt="Map of South Sound Hub - Kent, Renton, Auburn, Tacoma, Puyallup" className="w-full h-full object-cover transition-transform duration-[10000ms] group-hover:scale-[1.05]" />
          </div>

        </div>
      </div>

      <FAQSection routePath="/markets/south-sound" heading="South Sound & South King County FAQ" />
      <ContactSection />
    </div>
  );
}
