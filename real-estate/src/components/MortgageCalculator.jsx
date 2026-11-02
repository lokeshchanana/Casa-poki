import React, { useState, useMemo } from 'react';
import { Calculator, DollarSign, Percent, Calendar, ShieldCheck, Home, Info, Sparkles } from 'lucide-react';

export default function MortgageCalculator() {
  const [homePrice, setHomePrice] = useState(850000);
  const [downPaymentPercent, setDownPaymentPercent] = useState(20);
  const [interestRate, setInterestRate] = useState(6.75);
  const [loanTermYears, setLoanTermYears] = useState(30);
  const [propertyTaxRate, setPropertyTaxRate] = useState(1.1);
  const [annualInsurance, setAnnualInsurance] = useState(1500);
  const [monthlyHoa, setMonthlyHoa] = useState(0);

  const downPaymentAmount = useMemo(() => (homePrice * downPaymentPercent) / 100, [homePrice, downPaymentPercent]);
  const loanAmount = useMemo(() => homePrice - downPaymentAmount, [homePrice, downPaymentAmount]);

  const monthlyPrincipalAndInterest = useMemo(() => {
    if (loanAmount <= 0) return 0;
    const monthlyRate = interestRate / 100 / 12;
    const totalPayments = loanTermYears * 12;
    if (monthlyRate === 0) return loanAmount / totalPayments;
    
    return (
      (loanAmount * (monthlyRate * Math.pow(1 + monthlyRate, totalPayments))) /
      (Math.pow(1 + monthlyRate, totalPayments) - 1)
    );
  }, [loanAmount, interestRate, loanTermYears]);

  const monthlyPropertyTax = useMemo(() => (homePrice * (propertyTaxRate / 100)) / 12, [homePrice, propertyTaxRate]);
  const monthlyInsurance = useMemo(() => annualInsurance / 12, [annualInsurance]);

  const totalMonthlyPayment = useMemo(() => {
    return monthlyPrincipalAndInterest + monthlyPropertyTax + monthlyInsurance + Number(monthlyHoa);
  }, [monthlyPrincipalAndInterest, monthlyPropertyTax, monthlyInsurance, monthlyHoa]);

  const piPercent = (monthlyPrincipalAndInterest / totalMonthlyPayment) * 100 || 0;
  const taxPercent = (monthlyPropertyTax / totalMonthlyPayment) * 100 || 0;
  const insPercent = (monthlyInsurance / totalMonthlyPayment) * 100 || 0;
  const hoaPercent = (Number(monthlyHoa) / totalMonthlyPayment) * 100 || 0;

  return (
    <section id="calculator" className="py-24 bg-slate-100 dark:bg-navy-900 border-t border-b border-slate-200 dark:border-navy-800 transition-colors duration-300 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Title */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 bg-cyan/10 border border-cyan/30 px-4 py-1.5 rounded-full text-cyan-dark dark:text-cyan text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" /> Washington Financial Planning Tool
          </div>
          <h2 className="text-3xl sm:text-5xl font-serif font-extrabold text-slate-900 dark:text-white tracking-tight">
            Mortgage & Housing Payment Calculator
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-base sm:text-lg">
            Estimate your complete monthly housing payment including principal, interest, Washington State property taxes, insurance, and HOA dues.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          
          {/* Controls Column */}
          <div className="lg:col-span-7 bg-white dark:bg-navy-950 p-6 sm:p-9 rounded-3xl border border-slate-200 dark:border-navy-700 shadow-xl shadow-slate-200/50 dark:shadow-2xl space-y-6">
            
            {/* Home Price Input */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm font-semibold">
                <label className="text-slate-800 dark:text-slate-200">Home Purchase Price</label>
                <span className="text-cyan-dark dark:text-cyan font-extrabold text-xl">${homePrice.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min={200000}
                max={3000000}
                step={10000}
                value={homePrice}
                onChange={(e) => setHomePrice(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 dark:bg-navy-800 rounded-lg appearance-none cursor-pointer accent-cyan"
              />
              <div className="flex justify-between text-[11px] text-slate-400 font-medium">
                <span>$200k</span>
                <span>$1.5M</span>
                <span>$3.0M+</span>
              </div>
            </div>

            {/* Down Payment & Loan Term */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">Down Payment</label>
                <div className="relative flex items-center">
                  <input
                    type="number"
                    value={downPaymentPercent}
                    onChange={(e) => setDownPaymentPercent(Math.max(0, Math.min(100, Number(e.target.value))))}
                    className="w-full bg-slate-50 dark:bg-navy-900 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-bold focus:outline-none focus:border-cyan text-sm"
                  />
                  <span className="absolute right-3 text-cyan-dark dark:text-cyan font-bold">%</span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Down Payment Amount: <strong className="text-slate-900 dark:text-white">${Math.round(downPaymentAmount).toLocaleString()}</strong>
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">Interest Rate</label>
                <div className="relative flex items-center">
                  <input
                    type="number"
                    step="0.125"
                    value={interestRate}
                    onChange={(e) => setInterestRate(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-navy-900 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-bold focus:outline-none focus:border-cyan text-sm"
                  />
                  <span className="absolute right-3 text-cyan-dark dark:text-cyan font-bold">%</span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Current avg 30-year fixed rate</p>
              </div>

            </div>

            {/* Loan Term & Tax Rate */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">Loan Term</label>
                <select
                  value={loanTermYears}
                  onChange={(e) => setLoanTermYears(Number(e.target.value))}
                  className="w-full bg-slate-50 dark:bg-navy-900 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-bold focus:outline-none focus:border-cyan text-sm cursor-pointer"
                >
                  <option value={30}>30 Years Fixed</option>
                  <option value={20}>20 Years Fixed</option>
                  <option value={15}>15 Years Fixed</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">WA Property Tax Rate</label>
                <div className="relative flex items-center">
                  <input
                    type="number"
                    step="0.05"
                    value={propertyTaxRate}
                    onChange={(e) => setPropertyTaxRate(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-navy-900 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-bold focus:outline-none focus:border-cyan text-sm"
                  />
                  <span className="absolute right-3 text-cyan-dark dark:text-cyan font-bold">%</span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">King & Snohomish avg (~1.0–1.2%)</p>
              </div>

            </div>

            {/* Insurance & HOA */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">Home Insurance ($/yr)</label>
                <input
                  type="number"
                  step="100"
                  value={annualInsurance}
                  onChange={(e) => setAnnualInsurance(Number(e.target.value))}
                  className="w-full bg-slate-50 dark:bg-navy-900 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-bold focus:outline-none focus:border-cyan text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">Monthly HOA Dues ($/mo)</label>
                <input
                  type="number"
                  step="25"
                  value={monthlyHoa}
                  onChange={(e) => setMonthlyHoa(Number(e.target.value))}
                  className="w-full bg-slate-50 dark:bg-navy-900 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-bold focus:outline-none focus:border-cyan text-sm"
                />
              </div>

            </div>

          </div>

          {/* Results Column */}
          <div className="lg:col-span-5 bg-white dark:bg-navy-950 p-6 sm:p-9 rounded-3xl border border-cyan/30 shadow-2xl space-y-6 relative overflow-hidden">
            
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan/10 rounded-full blur-2xl pointer-events-none"></div>

            <div className="text-center pb-4 border-b border-slate-200 dark:border-navy-800">
              <p className="text-xs uppercase font-extrabold text-cyan-dark dark:text-cyan tracking-wider">Estimated Total Payment</p>
              <h3 className="text-4xl sm:text-5xl font-serif font-black text-slate-900 dark:text-white mt-1">
                ${Math.round(totalMonthlyPayment).toLocaleString()}<span className="text-base font-sans font-normal text-slate-500">/mo</span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Total Loan Amount: <strong className="text-slate-900 dark:text-slate-200">${loanAmount.toLocaleString()}</strong>
              </p>
            </div>

            {/* Stacked Payment Breakdown Bar */}
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase text-slate-500 dark:text-slate-400">Payment Breakdown Visual</p>
              <div className="w-full h-4 bg-slate-100 dark:bg-navy-800 rounded-full overflow-hidden flex shadow-inner">
                <div style={{ width: `${piPercent}%` }} className="bg-cyan transition-all duration-500" title="Principal & Interest"></div>
                <div style={{ width: `${taxPercent}%` }} className="bg-blue-500 transition-all duration-500" title="Property Taxes"></div>
                <div style={{ width: `${insPercent}%` }} className="bg-indigo-400 transition-all duration-500" title="Home Insurance"></div>
                <div style={{ width: `${hoaPercent}%` }} className="bg-emerald-400 transition-all duration-500" title="HOA Dues"></div>
              </div>
            </div>

            {/* Detailed List */}
            <div className="space-y-3 pt-2">
              
              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-navy-900 border border-slate-200 dark:border-navy-800">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-cyan"></span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Principal & Interest</span>
                </div>
                <span className="text-sm font-bold text-slate-900 dark:text-white">${Math.round(monthlyPrincipalAndInterest).toLocaleString()}</span>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-navy-900 border border-slate-200 dark:border-navy-800">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">WA Property Taxes</span>
                </div>
                <span className="text-sm font-bold text-slate-900 dark:text-white">${Math.round(monthlyPropertyTax).toLocaleString()}</span>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-navy-900 border border-slate-200 dark:border-navy-800">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-indigo-400"></span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Homeowners Insurance</span>
                </div>
                <span className="text-sm font-bold text-slate-900 dark:text-white">${Math.round(monthlyInsurance).toLocaleString()}</span>
              </div>

              {monthlyHoa > 0 && (
                <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-navy-900 border border-slate-200 dark:border-navy-800">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-emerald-400"></span>
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">HOA Dues</span>
                  </div>
                  <span className="text-sm font-bold text-slate-900 dark:text-white">${Math.round(monthlyHoa).toLocaleString()}</span>
                </div>
              )}

            </div>

            {/* Action Box */}
            <div className="p-4 rounded-2xl bg-cyan/10 border border-cyan/30 text-center space-y-3">
              <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                Need preferred lender recommendations or pre-approval guidance in Seattle?
              </p>
              <a
                href="#contact"
                className="inline-block bg-cyan hover:bg-cyan-light text-navy-950 font-extrabold text-xs px-6 py-3 rounded-xl shadow-lg shadow-cyan/20 transition-all"
              >
                Connect with Loki & Preferred Lenders
              </a>
            </div>

          </div>

        </div>
      </div>
    </section>
  );
}