
import React from 'react';

export default function TechnicalEdge() {
  return (
    <section id="approach" className="py-24 bg-ivory dark:bg-charcoal border-b border-silver/20 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          
          <div>
            <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">The Analytical Advantage</span>
            <h2 className="text-3xl md:text-5xl font-serif font-bold text-charcoal dark:text-silver mb-8 leading-tight">
              Data-Driven <br/>Real Estate Analytics.
            </h2>
            <p className="text-charcoal-light dark:text-silver-dark font-sans text-base leading-relaxed mb-8">
              My approach transitions real estate from an emotional transaction into a structured, highly analytical process. Utilizing deep market understanding, I build robust models to identify undervalued assets and optimal exit windows.
            </p>
            
            <ul className="space-y-6">
              <li className="flex items-start">
                <span className="w-1.5 h-1.5 rounded-full bg-charcoal dark:bg-silver mt-2 mr-4 shrink-0"></span>
                <p className="text-sm text-charcoal dark:text-silver-dark"><strong className="text-charcoal dark:text-silver">Predictive Pricing Models:</strong> Anticipating market shifts before they manifest in standard reporting.</p>
              </li>
              <li className="flex items-start">
                <span className="w-1.5 h-1.5 rounded-full bg-charcoal dark:bg-silver mt-2 mr-4 shrink-0"></span>
                <p className="text-sm text-charcoal dark:text-silver-dark"><strong className="text-charcoal dark:text-silver">Risk Mitigation:</strong> Comprehensive due diligence protocols engineered to protect capital.</p>
              </li>
              <li className="flex items-start">
                <span className="w-1.5 h-1.5 rounded-full bg-charcoal dark:bg-silver mt-2 mr-4 shrink-0"></span>
                <p className="text-sm text-charcoal dark:text-silver-dark"><strong className="text-charcoal dark:text-silver">Performance Tracking:</strong> Live data integration from NWMLS ensuring real-time asset evaluation.</p>
              </li>
            </ul>
          </div>

          <div className="relative border-4 border-silver/30 dark:border-silver/10 bg-ivory dark:bg-charcoal-dark p-2 sm:p-4 shadow-2xl rounded-xl flex items-center justify-center overflow-hidden w-full h-[550px]">
             <img 
               src="https://nwmls.stats.showingtime.com/infoserv/s-v1/tBqwv-fpe?w=550&h=550" 
               alt="Market Analytics Chart"
               className="w-full h-full object-contain dark:invert dark:hue-rotate-180 transition-all duration-500 mix-blend-multiply dark:mix-blend-screen"
             />
          </div>

        </div>
      </div>
    </section>
  );
}
