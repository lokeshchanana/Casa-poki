
import React from 'react';
import ContactSection from '../../components/ContactSection';
import FAQSection from '../../components/FAQSection';

export default function MarketPage() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="/hero_seattle.jpg" alt="Seattle Urban Core" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">Market Profile: Transit, Density & Split-Asset</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Seattle Urban Core</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Cities: Seattle, Shoreline, Lake Forest Park</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          
          <div className="font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-6">
            <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-8">Regional Analysis</h2>
            
<div className="space-y-4">
  <p>The Seattle Urban Core is the historic, cultural, and dense metropolitan heart of the region. Stretching from the southernmost borders of the city up through Shoreline and into the heavily forested enclaves of Lake Forest Park, this market is defined by its transit-oriented development and incredible architectural diversity.</p>
  <p>This is a market of split-asset classes. In neighborhoods like Queen Anne, Capitol Hill, and Magnolia, you will find historic Craftsman and Tudor homes commanding premium pricing for their charm and proximity to downtown. Conversely, South Lake Union and downtown Seattle offer ultra-dense, amenity-rich condominium living tailored to young professionals seeking a completely car-free, walkable lifestyle anchored by Amazon's global headquarters.</p>
  <p>As the Sound Transit Link Light Rail continues its aggressive expansion northward into Shoreline and beyond, zoning changes are rapidly transforming single-family plots into townhome and multi-family developments. This presents a unique landscape for investors seeking infill development opportunities and buyers looking to capitalize on appreciating transit corridors.</p>
</div>

            
            <div className="mt-12 p-8 bg-white dark:bg-charcoal-dark border border-silver/30">
               <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-6">Current Analytics</h3>
               <div className="grid grid-cols-2 gap-6">
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Avg Target Price</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">$880K+</p>
                 </div>
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Days on Market</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">14 Days</p>
                 </div>
               </div>
               <p className="text-xs text-silver-dark mt-6 italic">*Aggregated from recent NWMLS and regional reports. Market velocities shift rapidly.</p>
            </div>
          </div>

          <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-white dark:bg-charcoal-dark p-2 shadow-2xl rounded-xl h-[400px] lg:h-[600px] overflow-hidden group">
             <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-charcoal/20 to-transparent"></div>
             <img src="/map_seattle.jpg" alt="Map of Seattle Urban Core, Shoreline, and Lake Forest Park" className="w-full h-full object-cover transition-transform duration-[10000ms] group-hover:scale-[1.05]" />
          </div>

        </div>
      </div>

      <FAQSection routePath="/markets/seattle-core" heading="Seattle Urban Core FAQ" />
      <ContactSection />
    </div>
  );
}
