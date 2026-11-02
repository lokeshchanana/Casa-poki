import React, { useState } from 'react';
import { Phone, Mail, MapPin, Send, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { SocialCardsGrid } from './SocialLinks';

const CONTACT_PURPOSES = [
  { value: 'Buying a Home', label: 'Buying a Home' },
  { value: 'Selling a Home', label: 'Selling a Home' },
  { value: 'Home Valuation / What is My Home Worth?', label: 'Home Valuation / What is My Home Worth?' },
  { value: 'Relocating to Greater Seattle Area', label: 'Relocating to Greater Seattle Area' },
  { value: 'Investment & Multi-Family Property', label: 'Investment & Multi-Family Property' },
  { value: 'General Consultation', label: 'General Consultation / Other Question' }
];

export default function ContactSection() {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [purpose, setPurpose] = useState(CONTACT_PURPOSES[0].value);
  const [message, setMessage] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submittedData, setSubmittedData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handlePhoneChange = (e) => {
    const value = e.target.value;
    if (value.length < phone.length) {
      setPhone(value);
      return;
    }
    let digits = value.replace(/\D/g, '');
    if (digits.length === 11 && digits.startsWith('1')) {
      digits = digits.slice(1);
    }
    if (digits.length === 0) {
      setPhone('');
    } else if (digits.length <= 3) {
      setPhone(`(${digits}`);
    } else if (digits.length <= 6) {
      setPhone(`(${digits.slice(0, 3)}) ${digits.slice(3)}`);
    } else {
      setPhone(`(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');

    const payload = {
      name: name.trim(),
      phone: phone.trim(),
      email: email.trim().toLowerCase(),
      purpose: purpose,
      message: message.trim(),
      lead_source: 'Website'
    };

    try {
      const response = await fetch('https://n8n.lokeshchanana.com/webhook/website-contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const resData = await response.json().catch(() => ({ success: true }));
      if (resData && resData.success === false) {
        throw new Error(resData.error || resData.message || 'Failed to submit inquiry');
      }

      setSubmittedData({
        name: payload.name,
        phone: payload.phone,
        purpose: payload.purpose
      });
      setSubmitted(true);
    } catch (err) {
      console.error('Contact submission error:', err);
      setErrorMessage(
        'Unable to send inquiry automatically at this moment. Please call or text (801) 860-1052 directly, or email lokeshchanana@outlook.com.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setName('');
    setPhone('');
    setEmail('');
    setPurpose(CONTACT_PURPOSES[0].value);
    setMessage('');
    setSubmitted(false);
    setSubmittedData(null);
    setErrorMessage('');
  };

  return (
    <section id="contact" className="py-24 bg-ivory dark:bg-charcoal transition-colors duration-300 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          
          {/* Left Info Panel */}
          <div>
            <div className="flex items-center gap-6 mb-6">
              <img src="/loki-profile.jpg" alt="Lokesh Chanana" className="w-24 h-24 sm:w-32 sm:h-32 rounded-full object-cover object-[50%_25%] border-2 border-silver/50 dark:border-silver/20 shadow-md scale-x-[-1]" />
              <div>
                <h2 className="text-3xl md:text-4xl font-serif font-bold text-charcoal dark:text-silver mb-2">Lokesh Chanana</h2>
                <p className="text-charcoal-light dark:text-silver-dark font-sans text-sm tracking-widest uppercase">
                  (Loki)
                </p>
              </div>
            </div>
            <p className="text-charcoal-light dark:text-silver-dark font-sans text-sm mb-12">
              For discrete inquiries, market valuations, or to discuss your specific real estate requirements in Greater Seattle.
            </p>
            
            <div className="space-y-8">
              <a href="tel:8018601052" className="flex items-center gap-6 group">
                <div className="p-4 border border-silver/40 dark:border-silver/20 text-charcoal dark:text-silver group-hover:bg-charcoal group-hover:text-ivory dark:group-hover:bg-silver dark:group-hover:text-charcoal transition-colors">
                  <Phone className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold">Direct Line</p>
                  <p className="text-lg font-serif font-bold text-charcoal dark:text-silver">(801) 860-1052</p>
                </div>
              </a>

              <a href="mailto:lokeshchanana@outlook.com" className="flex items-center gap-6 group">
                <div className="p-4 border border-silver/40 dark:border-silver/20 text-charcoal dark:text-silver group-hover:bg-charcoal group-hover:text-ivory dark:group-hover:bg-silver dark:group-hover:text-charcoal transition-colors">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold">Email</p>
                  <p className="text-sm font-sans font-medium text-charcoal dark:text-silver">lokeshchanana@outlook.com</p>
                </div>
              </a>
              
              <div className="flex items-center gap-6">
                <div className="p-4 border border-silver/40 dark:border-silver/20 text-charcoal dark:text-silver">
                  <MapPin className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold">Operating Region</p>
                  <p className="text-sm font-sans font-medium text-charcoal dark:text-silver">Greater Seattle, Washington</p>
                </div>
              </div>
            </div>

            {/* Online Profiles & Reviews */}
            <div className="mt-8 pt-8 border-t border-silver/20">
              <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-3">Online Profiles & Client Reviews</p>
              <SocialCardsGrid />
            </div>

            <div className="mt-10 pt-8 border-t border-silver/20 grid grid-cols-2 gap-4">
               <div>
                 <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4">Brokerage</p>
                 <a href="https://onereal.com/" target="_blank" rel="noopener noreferrer"><img src="/real-logo.png" alt="REAL Broker LLC" className="h-16 object-contain dark:invert hover:opacity-80 transition-opacity" /></a>
               </div>
               <div>
                 <p className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4">Team Affiliation</p>
                 <a href="https://lakhaniteamre.com/" target="_blank" rel="noopener noreferrer"><img src="/lakhani-logo.png" alt="Lakhani Realtors" className="h-20 object-contain invert dark:invert-0 hover:opacity-80 transition-opacity" /></a>
               </div>
            </div>
          </div>

          {/* Right Form Panel */}
          <div className="bg-white dark:bg-charcoal-dark p-8 md:p-12 border border-silver/30 dark:border-silver/10 shadow-lg flex flex-col justify-center">
            {submitted ? (
              <div className="py-8 space-y-6 text-center animate-fade-in">
                <div className="w-16 h-16 mx-auto rounded-full bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shadow-sm">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                
                <div>
                  <h3 className="text-2xl font-serif font-bold text-charcoal dark:text-silver mb-2">
                    Thank You, {submittedData?.name || 'Valued Client'}!
                  </h3>
                  <p className="text-charcoal-light dark:text-silver-dark text-sm max-w-md mx-auto leading-relaxed">
                    Your inquiry regarding <strong className="text-charcoal dark:text-silver font-semibold">{submittedData?.purpose}</strong> has been received directly into Loki's desk. Loki will review your requirements and reach out shortly.
                  </p>
                </div>

                {submittedData?.phone && (
                  <div className="p-4 bg-ivory dark:bg-charcoal border border-silver/30 dark:border-silver/20 rounded-lg max-w-md mx-auto text-left">
                    <p className="text-xs font-semibold text-charcoal dark:text-silver mb-1 flex items-center gap-1.5">
                      <span>📱 Instant Mobile Confirmation</span>
                    </p>
                    <p className="text-[11px] text-charcoal-light dark:text-silver-dark leading-relaxed">
                      An automated confirmation text containing Loki's digital vCard has been dispatched to <span className="font-mono font-medium text-charcoal dark:text-silver">{submittedData.phone}</span>.
                    </p>
                  </div>
                )}

                <div className="pt-4">
                  <button
                    type="button"
                    onClick={handleReset}
                    className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-charcoal dark:text-silver border-b border-charcoal/40 dark:border-silver/40 pb-1 hover:border-charcoal dark:hover:border-silver transition-all"
                  >
                    <span>Send Another Inquiry</span>
                    <span>&rarr;</span>
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <h3 className="font-serif font-bold text-xl text-charcoal dark:text-silver mb-1">
                    Send a Message
                  </h3>
                  <p className="text-xs text-charcoal-light dark:text-silver-dark">
                    Direct confidential contact. Inquiries are routed immediately to Loki.
                  </p>
                </div>

                {errorMessage && (
                  <div className="p-3.5 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800 text-red-700 dark:text-red-300 rounded text-xs flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{errorMessage}</span>
                  </div>
                )}

                {/* Full Name */}
                <div>
                  <label htmlFor="contact-name" className="text-[10px] font-bold uppercase tracking-widest text-charcoal dark:text-silver-dark block mb-2">
                    Full Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="contact-name"
                    type="text"
                    name="name"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Jane Doe"
                    autoComplete="name"
                    className="w-full bg-ivory dark:bg-charcoal border-b border-silver/50 dark:border-silver/30 px-0 py-2 text-charcoal dark:text-silver focus:outline-none focus:border-charcoal dark:focus:border-silver text-sm font-sans placeholder:text-silver-dark/60 transition-colors"
                  />
                </div>

                {/* Phone & Email side by side */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="contact-phone" className="text-[10px] font-bold uppercase tracking-widest text-charcoal dark:text-silver-dark block mb-2">
                      Phone Number
                    </label>
                    <input
                      id="contact-phone"
                      type="tel"
                      inputMode="tel"
                      name="phone"
                      value={phone}
                      onChange={handlePhoneChange}
                      placeholder="(801) 555-0123"
                      autoComplete="tel"
                      className="w-full bg-ivory dark:bg-charcoal border-b border-silver/50 dark:border-silver/30 px-0 py-2 text-charcoal dark:text-silver focus:outline-none focus:border-charcoal dark:focus:border-silver text-sm font-sans placeholder:text-silver-dark/60 transition-colors"
                    />
                    <span className="text-[10px] text-silver-dark block mt-1">Optional, receive instant SMS & vCard</span>
                  </div>
                  <div>
                    <label htmlFor="contact-email" className="text-[10px] font-bold uppercase tracking-widest text-charcoal dark:text-silver-dark block mb-2">
                      Email Address <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="contact-email"
                      type="email"
                      inputMode="email"
                      name="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@example.com"
                      autoComplete="email"
                      className="w-full bg-ivory dark:bg-charcoal border-b border-silver/50 dark:border-silver/30 px-0 py-2 text-charcoal dark:text-silver focus:outline-none focus:border-charcoal dark:focus:border-silver text-sm font-sans placeholder:text-silver-dark/60 transition-colors"
                    />
                  </div>
                </div>

                {/* Purpose of Contact */}
                <div>
                  <label htmlFor="contact-purpose" className="text-[10px] font-bold uppercase tracking-widest text-charcoal dark:text-silver-dark block mb-2">
                    Purpose of Contact <span className="text-rose-500">*</span>
                  </label>
                  <select
                    id="contact-purpose"
                    name="purpose"
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    className="w-full bg-ivory dark:bg-charcoal border-b border-silver/50 dark:border-silver/30 px-0 py-2.5 text-charcoal dark:text-silver focus:outline-none focus:border-charcoal dark:focus:border-silver text-sm font-sans cursor-pointer transition-colors"
                  >
                    {CONTACT_PURPOSES.map((p) => (
                      <option key={p.value} value={p.value} className="bg-white dark:bg-charcoal-dark text-charcoal dark:text-silver py-1">
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Inquiry Details */}
                <div>
                  <label htmlFor="contact-message" className="text-[10px] font-bold uppercase tracking-widest text-charcoal dark:text-silver-dark block mb-2">
                    Inquiry Details <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    id="contact-message"
                    rows={3}
                    name="message"
                    required
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Tell Loki about your timeline, ideal neighborhood, property goals, or questions..."
                    className="w-full bg-ivory dark:bg-charcoal border-b border-silver/50 dark:border-silver/30 px-0 py-2 text-charcoal dark:text-silver focus:outline-none focus:border-charcoal dark:focus:border-silver text-sm font-sans placeholder:text-silver-dark/60 transition-colors resize-none"
                  ></textarea>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-3 bg-charcoal hover:bg-charcoal-light dark:bg-silver dark:hover:bg-white text-ivory dark:text-charcoal py-4 text-xs font-bold uppercase tracking-widest transition-colors mt-8 disabled:opacity-60 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Sending Inquiry...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Submit Inquiry</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>

        </div>

      </div>
    </section>
  );
}