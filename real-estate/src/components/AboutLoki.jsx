import React from 'react';
import { ShieldCheck, HeartHandshake, MapPin, Award, CheckCircle, ExternalLink, Phone, Mail, Sparkles } from 'lucide-react';
import { SOCIAL_PROFILES } from './SocialLinks';

export default function AboutLoki() {
  return (
    <section id="about" className="py-24 bg-slate-50 dark:bg-navy-950 transition-colors duration-300 relative border-b border-slate-200 dark:border-navy-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Standing Portrait Showcase */}
          <div className="lg:col-span-5 relative">
            <div className="relative rounded-3xl overflow-hidden border-2 border-cyan/30 shadow-2xl bg-white dark:bg-navy-900 p-3">
              <img 
                src="/media_1788298898972.png" 
                alt="Lokesh Chanana (Loki) - Real Estate Agent" 
                className="w-full h-[520px] object-cover object-top rounded-2xl"
              />
            </div>

            {/* Motto Badge Card */}
            <div className="mt-6 bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 p-5 rounded-2xl shadow-xl flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-cyan/15 border border-cyan/30 flex items-center justify-center text-cyan text-2xl font-serif font-bold shrink-0">
                L
              </div>
              <div>
                <p className="text-[10px] uppercase font-extrabold text-cyan-dark dark:text-cyan tracking-wider">Personal Motto</p>
                <h4 className="text-slate-900 dark:text-white font-serif font-bold text-lg">"WORK HARD. Be Kind."</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400">Unwavering dedication to every buyer & seller.</p>
              </div>
            </div>
          </div>

          {/* Bio & Details */}
          <div className="lg:col-span-7 space-y-6">
            
            <div className="inline-flex items-center gap-2 bg-cyan/10 border border-cyan/30 px-4 py-1.5 rounded-full text-cyan-dark dark:text-cyan text-xs font-bold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" /> About Your Realtor®
            </div>

            <h2 className="text-3xl sm:text-5xl font-serif font-extrabold text-slate-900 dark:text-white tracking-tight">
              Lokesh Chanana <span className="text-cyan-dark dark:text-cyan font-sans text-2xl font-semibold">(Loki)</span>
            </h2>

            <p className="text-slate-700 dark:text-slate-300 text-base sm:text-lg leading-relaxed font-normal">
              Licensed in Washington State, I represent home buyers, sellers, and investors across <strong className="text-slate-900 dark:text-white font-semibold">Seattle, Bellevue, Kirkland, Redmond, Renton, and surrounding King, Snohomish, and Pierce counties</strong>.
            </p>

            <p className="text-slate-600 dark:text-slate-300 text-base leading-relaxed">
              In partnership with <strong className="text-slate-900 dark:text-white font-semibold">REAL Broker LLC</strong> and the premier <strong className="text-slate-900 dark:text-white font-semibold">Lakhani Team Real Estate</strong>, I bring bespoke digital strategy, clear communication, and precise local market valuation to help you achieve your goals effortlessly.
            </p>

            {/* Key Pillars Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              
              <div className="p-4 rounded-2xl bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-800 shadow-sm space-y-2">
                <div className="flex items-center gap-2 text-cyan-dark dark:text-cyan font-bold text-sm">
                  <MapPin className="w-4 h-4" /> Greater Seattle Local Expertise
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Comprehensive understanding of neighborhood trends across Seattle, King County, and the Eastside tech corridor.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-800 shadow-sm space-y-2">
                <div className="flex items-center gap-2 text-cyan-dark dark:text-cyan font-bold text-sm">
                  <HeartHandshake className="w-4 h-4" /> Fiduciary Advocacy
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Your priorities guide every conversation, negotiation strategy, and closing contract detail.
                </p>
              </div>

            </div>

            {/* Brokerage & Team Links */}
            <div className="pt-4 border-t border-slate-200 dark:border-navy-800 flex flex-wrap items-center gap-6">
              <a 
                href="https://onereal.com/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300 hover:text-cyan transition-colors"
              >
                <span>REAL Broker LLC (onereal.com/loki)</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>

              <a 
                href="https://lakhaniteamre.com/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300 hover:text-cyan transition-colors"
              >
                <span>Lakhani Team Real Estate</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Social Media & Client Reviews */}
            <div className="pt-4 border-t border-slate-200 dark:border-navy-800 space-y-3">
              <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400">
                Connect Online & Read Client Reviews
              </p>
              <div className="flex flex-wrap items-center gap-2.5">
                {SOCIAL_PROFILES.map((item) => {
                  const Icon = item.Icon;
                  return (
                    <a
                      key={item.name}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-navy-700 bg-white dark:bg-navy-900 text-xs font-semibold text-slate-700 dark:text-slate-300 ${item.hoverText} ${item.hoverBorder} transition-all shadow-sm`}
                    >
                      <Icon className="w-4 h-4 shrink-0" />
                      <span>{item.label}</span>
                      <ExternalLink className="w-3 h-3 opacity-60" />
                    </a>
                  );
                })}
              </div>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
}