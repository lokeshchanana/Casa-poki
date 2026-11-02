
import React from 'react';
import ContactSection from '../components/ContactSection';
import { SocialIconRow } from '../components/SocialLinks';
import InstagramReels from '../components/InstagramReels';
import FAQSection from '../components/FAQSection';

export default function AboutLoki() {
  return (
    <div className="bg-ivory dark:bg-charcoal min-h-screen text-charcoal dark:text-silver transition-colors duration-300">
      <div className="pt-32 pb-24 max-w-6xl mx-auto px-4 sm:px-6 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <div className="order-2 md:order-1 space-y-6">
          <h1 className="text-4xl md:text-5xl font-serif font-bold">About Lokesh Chanana</h1>
          <p className="text-[12px] uppercase tracking-[0.2em] font-semibold text-silver-dark">Real Estate Agent (Loki)</p>
          <div className="font-sans text-charcoal-light dark:text-silver-dark leading-relaxed space-y-4">
            <p>With over 15 years of experience in IT and Systems Analytics, I approach real estate differently. I believe that data, precision, and process engineering are just as important as relationships in today's complex market.</p>
            <p>Operating primarily in Greater Seattle, I leverage deep micro-market intelligence to help buyers find hidden value and sellers maximize their return on investment.</p>
            <p>In partnership with REAL Broker LLC and the Lakhani Team Real Estate, I bring a unique blend of white-glove service and analytical rigor to every transaction.</p>
          </div>
          <div className="pt-2">
            <p className="text-[10px] uppercase font-bold tracking-widest text-silver-dark mb-3">Connect With Me</p>
            <SocialIconRow size="md" />
          </div>
        </div>
        <div className="order-1 md:order-2">
           <div className="relative p-4 bg-white dark:bg-charcoal-dark border border-silver/30 shadow-2xl">
             <div className="absolute inset-0 bg-cyan/5 -translate-x-4 -translate-y-4 -z-10 border border-cyan/20"></div>
             <img src="/loki-profile.jpg" alt="Lokesh Chanana" className="w-full h-auto object-cover grayscale-[20%]" />
           </div>
        </div>
      </div>
      <InstagramReels
        title="Loki's Video Tours & Field Walkthroughs"
        subtitle="Watch latest on-the-ground home inspections, open houses, and neighborhood tours."
      />
      <FAQSection routePath="/about" heading="About Lokesh 'Loki' Chanana — FAQ" />
      <ContactSection />
    </div>
  );
}
