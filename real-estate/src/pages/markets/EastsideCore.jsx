
import React from 'react';
import ContactSection from '../../components/ContactSection';
import FAQSection from '../../components/FAQSection';

export default function MarketPage() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="/hero_eastside.jpg" alt="Eastside Tech Core" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">Market Profile: High-Basis Innovation Corridor</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">Eastside Tech Core</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Cities: Bellevue, Kirkland, Redmond, Sammamish, Issaquah, Woodinville</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          
          <div className="font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-6">
            <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-8">Regional Analysis</h2>
            
<div className="space-y-4">
  <p>The Eastside Tech Core, encompassing the thriving municipalities of Bellevue, Kirkland, Redmond, Sammamish, Issaquah, and Woodinville, serves as the economic and technological powerhouse of the Pacific Northwest. Often referred to as the Silicon Valley of the North, this region is fundamentally anchored by the massive corporate campuses of Microsoft, Amazon, Meta, and a rapidly expanding ecosystem of tech startups.</p>
  <p>Real estate within this high-basis innovation corridor is characterized by exceptional appreciation, driven heavily by high-income tech demographics and constrained luxury inventory. The architectural landscape ranges from hyper-modern new construction in West Bellevue to expansive, equestrian-style estates in Woodinville’s famed wine country. Kirkland offers a premier waterfront lifestyle on Lake Washington, blending boutique urban walkability with resort-like exclusivity.</p>
  <p>For buyers, the Eastside is fiercely competitive but offers unparalleled access to the state's highest-rated public school districts, immaculate parks, and world-class retail infrastructure. For sellers and investors, the sustained influx of specialized talent provides a deep, recession-resistant buyer pool that continually pushes property values upward.</p>
</div>

            
            <div className="mt-12 p-8 bg-white dark:bg-charcoal-dark border border-silver/30">
               <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-6">Current Analytics</h3>
               <div className="grid grid-cols-2 gap-6">
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Avg Target Price</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">$1.4M+</p>
                 </div>
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Days on Market</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">10 Days</p>
                 </div>
               </div>
               <p className="text-xs text-silver-dark mt-6 italic">*Aggregated from recent NWMLS and regional reports. Market velocities shift rapidly.</p>
            </div>
          </div>

          <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-white dark:bg-charcoal-dark p-2 shadow-2xl rounded-xl h-[400px] lg:h-[600px] overflow-hidden group">
             <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-charcoal/20 to-transparent"></div>
             <img src="/map_eastside.jpg" alt="Map of Eastside Tech Core - Bellevue, Kirkland, Redmond, Sammamish" className="w-full h-full object-cover transition-transform duration-[10000ms] group-hover:scale-[1.05]" />
          </div>

        </div>
      </div>

      <FAQSection routePath="/markets/eastside-core" heading="Eastside Tech Core FAQ" />
      <ContactSection />
    </div>
  );
}
