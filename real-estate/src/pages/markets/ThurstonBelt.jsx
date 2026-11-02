
import React from 'react';
import ContactSection from '../../components/ContactSection';
import FAQSection from '../../components/FAQSection';

export default function MarketPage() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="/hero_thurston.jpg" alt="Capital & Exurban Fringe" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">Market Profile: State Govt & Space Value</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Capital & Exurban Fringe</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Cities: Olympia, Lacey, Tumwater, Yelm</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          
          <div className="font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-6">
            <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-8">Regional Analysis</h2>
            
<div className="space-y-4">
  <p>The Capital & Exurban Fringe, encompassing Thurston County municipalities like Olympia, Lacey, Tumwater, and Yelm, represents the southernmost boundary of the Greater Seattle economic sphere. This region is fundamentally stabilized by the Washington State government, which provides a massive, highly recession-resistant employment base.</p>
  <p>Real estate here is defined by immense space value. Buyers migrating to the Thurston Belt are typically seeking acreage, equestrian properties, or substantial square footage that would be cost-prohibitive in King or Pierce counties. Olympia, the state capital, offers a vibrant, independent cultural scene and historic waterfront, while Lacey and Tumwater have seen explosive growth in master-planned communities and modern retail centers.</p>
  <p>In the era of remote work, the Exurban Fringe has seen unprecedented demand. Families and professionals are willingly trading proximity to Seattle for a slower pace of life, massive evergreen-lined properties, and direct access to the natural wonders of the South Sound and the Olympic Peninsula, all while maintaining connectivity to the I-5 corridor.</p>
</div>

            
            <div className="mt-12 p-8 bg-white dark:bg-charcoal-dark border border-silver/30">
               <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-6">Current Analytics</h3>
               <div className="grid grid-cols-2 gap-6">
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Avg Target Price</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">$510K+</p>
                 </div>
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Days on Market</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">22 Days</p>
                 </div>
               </div>
               <p className="text-xs text-silver-dark mt-6 italic">*Aggregated from recent NWMLS and regional reports. Market velocities shift rapidly.</p>
            </div>
          </div>

          <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-white dark:bg-charcoal-dark p-2 shadow-2xl rounded-xl h-[400px] lg:h-[600px] overflow-hidden group">
             <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-charcoal/20 to-transparent"></div>
             <img src="/map_thurston.jpg" alt="Map of Thurston County - Olympia, Lacey, Tumwater, Yelm" className="w-full h-full object-cover transition-transform duration-[10000ms] group-hover:scale-[1.05]" />
          </div>

        </div>
      </div>

      <FAQSection routePath="/markets/thurston-belt" heading="Thurston County & Capital Region FAQ" />
      <ContactSection />
    </div>
  );
}
