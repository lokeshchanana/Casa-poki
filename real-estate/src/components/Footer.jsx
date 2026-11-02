import React from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { SocialIconRow, SOCIAL_PROFILES } from './SocialLinks';

export default function Footer() {
  return (
    <footer className="bg-white dark:bg-charcoal-dark border-t border-silver/20 pt-16 pb-12 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center md:text-left">
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 border-b border-silver/20 pb-12 mb-8">
          
          <div>
             <img src="/lc-logo.png" alt="Lc" className="h-20 w-auto mx-auto md:mx-0 mb-4 opacity-80" />
             <h3 className="font-serif font-bold text-lg text-charcoal dark:text-silver uppercase tracking-widest">Lokesh Chanana</h3>
             <p className="text-[10px] font-sans text-charcoal-light dark:text-silver-dark uppercase tracking-widest mt-1">Real Estate Agent (Loki)</p>
             <div className="mt-4 flex justify-center md:justify-start">
               <SocialIconRow size="sm" />
             </div>
          </div>

          <div className="lg:border-l border-silver/20 lg:pl-8">
             <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4">Official Partnerships</p>
             <div className="space-y-4 flex flex-col items-center md:items-start">
               <a href="https://onereal.com/" target="_blank" rel="noopener noreferrer"><img src="/real-logo.png" alt="REAL Broker LLC" className="h-9 object-contain dark:invert hover:opacity-80 transition-opacity" /></a>
               <a href="https://lakhaniteamre.com/" target="_blank" rel="noopener noreferrer"><img src="/lakhani-logo.png" alt="Lakhani Realtors" className="h-12 object-contain invert dark:invert-0 hover:opacity-80 transition-opacity" /></a>
             </div>
          </div>

          <div className="lg:border-l border-silver/20 lg:pl-8">
             <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4">Connect & Reviews</p>
             <ul className="space-y-2.5 text-xs font-sans">
               {SOCIAL_PROFILES.map((item) => {
                 const Icon = item.Icon;
                 return (
                   <li key={item.name} className="flex justify-center md:justify-start">
                     <a
                       href={item.url}
                       target="_blank"
                       rel="noopener noreferrer"
                       className={`inline-flex items-center gap-2 text-charcoal-light dark:text-silver-dark ${item.hoverText} transition-colors group`}
                     >
                       <Icon className="w-3.5 h-3.5 shrink-0 opacity-80 group-hover:opacity-100" />
                       <span className="font-medium">{item.label}</span>
                       <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                     </a>
                   </li>
                 );
               })}
             </ul>
          </div>

          <div className="lg:border-l border-silver/20 lg:pl-8">
             <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4">Core Service Cities</p>
             <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs font-sans mb-6">
               <Link to="/cities/kent" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Kent, WA</Link>
               <Link to="/cities/bellevue" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Bellevue, WA</Link>
               <Link to="/cities/seattle" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Seattle, WA</Link>
               <Link to="/cities/redmond" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Redmond, WA</Link>
               <Link to="/cities/kirkland" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Kirkland, WA</Link>
               <Link to="/cities/renton" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Renton, WA</Link>
               <Link to="/cities/auburn" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Auburn, WA</Link>
               <Link to="/cities/tacoma" className="text-charcoal-light dark:text-silver-dark hover:text-charcoal dark:hover:text-silver transition-colors">Tacoma, WA</Link>
             </div>
             <p className="text-[10px] text-charcoal-light dark:text-silver-dark leading-relaxed font-sans">
               Equal Housing Opportunity. Information deemed reliable but not guaranteed. 
               All real estate advertising is subject to the Federal Fair Housing Act.
             </p>
          </div>

        </div>

        <div className="flex flex-col md:flex-row justify-between items-center text-[10px] text-silver-dark font-sans uppercase tracking-widest">
          <p>© {new Date().getFullYear()} Lokesh Chanana. All Rights Reserved.</p>
          <p className="mt-4 md:mt-0">Greater Seattle, WA</p>
        </div>

      </div>
    </footer>
  );
}