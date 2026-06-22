import React, { useState } from 'react';

const faqs = [
  {
    question: "Is my data secure with FlexiAnalyse?",
    answer: "Absolutely. We use enterprise-grade encryption and comply with GDPR, ISO 27001, and other industry standards to ensure your data is always protected."
  },
  {
    question: "How do I get started with FlexiAnalyse?",
    answer: "Simply click 'Get Started Now' and create your account. You'll have instant access to our platform with no credit card required."
  },
  {
    question: "What industries does FlexiAnalyse support?",
    answer: "FlexiAnalyse is designed for multiple industries including healthcare, finance, retail, education, and manufacturing. Each industry benefits from tailored AI solutions."
  },
  {
    question: "Can I try FlexiAnalyse before committing?",
    answer: "Yes! We offer a free trial with full access to all features. You can experience the power of FlexiAnalyse risk-free for 14 days."
  },
  {
    question: "How does FlexiAnalyse compare to other AI tools?",
    answer: "FlexiAnalyse combines multiple advanced AI models working in harmony, delivering unmatched accuracy and efficiency compared to single-model solutions."
  }
];

const FAQSection: React.FC = () => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const toggleFAQ = (index: number) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  return (
    <section className="py-14 bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-16">
          Frequently Asked Questions
        </h2>
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div key={index} className="bg-white rounded-xl shadow-sm">
              <button
                onClick={() => toggleFAQ(index)}
                className="w-full p-6 text-left flex justify-between items-center"
              >
                <span className="font-semibold text-gray-900">{faq.question}</span>
                <span className={`transform transition-transform ${activeIndex === index ? 'rotate-180' : ''}`}>
                  <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </button>
              <div className={`px-6 pb-6 ${activeIndex === index ? 'block' : 'hidden'}`}>
                <p className="text-gray-600">{faq.answer}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FAQSection;