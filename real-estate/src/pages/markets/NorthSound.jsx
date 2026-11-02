
import React from 'react';
import ContactSection from '../../components/ContactSection';
import FAQSection from '../../components/FAQSection';

export default function MarketPage() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="relative pt-32 pb-24 bg-charcoal dark:bg-charcoal-dark border-b border-silver/20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src="/hero_north.jpg" alt="North Sound Corridor" className="w-full h-full object-cover opacity-20 grayscale" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">Market Profile: Sprawl & Norming Absorption</span>
          <h1 className="text-4xl md:text-6xl font-serif font-bold text-ivory dark:text-silver mb-6">North Sound Corridor</h1>
          <p className="text-silver-dark font-sans text-lg max-w-2xl mx-auto">Cities: Lynnwood, Edmonds, Bothell, Everett, Marysville</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          
          <div className="font-sans leading-relaxed text-charcoal-light dark:text-silver-dark space-y-6">
            <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-8">Regional Analysis</h2>
            
<div className="space-y-4">
  <p>The North Sound Corridor, stretching through Snohomish County and encompassing Lynnwood, Edmonds, Bothell, Everett, and Marysville, represents the primary vector for suburban sprawl and norming absorption in the Greater Seattle area. As pricing in the urban core and Eastside reaches historic highs, the North Sound has become the premier destination for buyers seeking square footage, traditional neighborhood infrastructure, and relative affordability.</p>
  <p>This region is far from just a bedroom community; it is an economic engine in its own right. Everett is deeply anchored by Boeing and the aerospace industry, while Bothell has quietly transformed into a major biotechnology and life sciences hub. Edmonds provides a picturesque, historic waterfront downtown that rivals the charm of the Eastside, complete with ferry access to the Olympic Peninsula.</p>
  <p>With the imminent arrival of light rail extensions into Lynnwood and eventually Everett, the North Sound Corridor is undergoing a massive infrastructural renaissance. Investors are highly active here, capitalizing on the reliable demand from first-time homebuyers and families prioritizing lot size and community amenities over urban density.</p>
</div>

            
            <div className="mt-12 p-8 bg-white dark:bg-charcoal-dark border border-silver/30">
               <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-6">Current Analytics</h3>
               <div className="grid grid-cols-2 gap-6">
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Avg Target Price</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">$740K+</p>
                 </div>
                 <div>
                   <p className="text-[10px] uppercase tracking-widest text-silver-dark mb-1">Days on Market</p>
                   <p className="font-serif font-bold text-2xl text-charcoal dark:text-silver">18 Days</p>
                 </div>
               </div>
               <p className="text-xs text-silver-dark mt-6 italic">*Aggregated from recent NWMLS and regional reports. Market velocities shift rapidly.</p>
            </div>
          </div>

          <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-white dark:bg-charcoal-dark p-2 shadow-2xl rounded-xl h-[400px] lg:h-[600px] overflow-hidden group">
             <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-charcoal/20 to-transparent"></div>
             <img src="/map_north.jpg" alt="Map of North Sound Corridor - Bothell, Lynnwood, Edmonds, Everett" className="w-full h-full object-cover transition-transform duration-[10000ms] group-hover:scale-[1.05]" />
          </div>

        </div>
      </div>

      <FAQSection routePath="/markets/north-sound" heading="North Sound Corridor FAQ" />
      <ContactSection />
    </div>
  );
}
