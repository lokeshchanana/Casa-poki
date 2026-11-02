import React from 'react';
import { Home, Hammer, EyeOff } from 'lucide-react';

const CARDS = [
  {
    title: 'Standard Market Valuation',
    icon: <Home className="w-6 h-6" />,
    description: 'A precise assessment of your property based on current, hyper-local comparative data in King County.',
    deliverables: ['Comparative Market Analysis (CMA)', 'Neighborhood Velocity Metrics', 'Pricing Strategy Report']
  },
  {
    title: 'Renovation-Adjusted Valuation',
    icon: <Hammer className="w-6 h-6" />,
    description: 'Calculated ROI analysis for specific property improvements. Know exactly which upgrades yield the highest return before listing.',
    deliverables: ['Pre vs Post-Renovation ARV', 'Cost-to-Value Matrix', 'Contractor Guidance']
  },
  {
    title: 'Off-Market Analysis',
    icon: <EyeOff className="w-6 h-6" />,
    description: 'Discreet evaluation for sellers preferring privacy. Assessment of direct-buyer networks and institutional interest.',
    deliverables: ['Private Network Matching', 'Pocket Listing Viability', 'Discreet Marketing Plan']
  }
];

export default function ValuationCards() {
  return (
    <section id="valuation" className="py-24 bg-white dark:bg-charcoal-dark border-b border-silver/20 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl font-serif font-bold text-charcoal dark:text-silver mb-4">Strategic Valuation Frameworks</h2>
          <p className="text-charcoal-light dark:text-silver-dark font-sans text-sm leading-relaxed">
            Select the analytical approach that aligns with your timeline and objectives.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {CARDS.map((card) => (
            <div key={card.title} className="bg-ivory dark:bg-charcoal border border-silver/30 dark:border-silver/20 p-8 flex flex-col group hover:border-charcoal dark:hover:border-silver transition-colors">
              <div className="mb-6 p-4 inline-block bg-white dark:bg-charcoal-dark border border-silver/20 text-charcoal dark:text-silver">
                {card.icon}
              </div>
              
              <h3 className="text-lg font-serif font-bold text-charcoal dark:text-silver mb-3">{card.title}</h3>
              <p className="text-sm font-sans text-charcoal-light dark:text-silver-dark mb-8 flex-1">
                {card.description}
              </p>
              
              <div className="mb-8">
                <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-3 border-b border-silver/20 pb-2">Key Deliverables</p>
                <ul className="space-y-2">
                  {card.deliverables.map((item, i) => (
                    <li key={i} className="text-xs font-sans text-charcoal-light dark:text-silver-dark flex items-center gap-2">
                      <span className="w-1 h-1 bg-charcoal dark:bg-silver rounded-full"></span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              <a href="#contact" className="mt-auto block text-center w-full bg-transparent border border-charcoal dark:border-silver text-charcoal dark:text-silver hover:bg-charcoal hover:text-ivory dark:hover:bg-silver dark:hover:text-charcoal py-3 text-xs uppercase font-bold tracking-widest transition-colors">
                Request Analysis
              </a>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}