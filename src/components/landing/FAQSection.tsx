import React, { useState } from 'react';

const faqs = [
  {
    question: "Which databases does FlexiAnalyse work with?",
    answer: "SQL databases: PostgreSQL, MySQL / MariaDB, SQL Server, Oracle and more. You can connect a managed database in the cloud, or a database running inside your own network."
  },
  {
    question: "Can it reach a database on-premise or behind a firewall?",
    answer: "Yes. For private databases, you run a lightweight agent inside your network. It dials out to FlexiAnalyse over an encrypted channel, so you never open an inbound port or expose your database. Your credentials stay on your side; only query results transit."
  },
  {
    question: "Can it modify my data, or only read it?",
    answer: "Read-only by default. The agent only reads unless you explicitly enable writes, and even then every UPDATE / INSERT / DELETE is previewed first and commits only after your explicit confirmation."
  },
  {
    question: "How do I know an answer is correct?",
    answer: "Every answer is produced by a real SQL query run against your data, and that exact query is shown alongside the result, so you can always verify the work. If a question can't be answered from your schema, the agent tells you instead of guessing."
  },
  {
    question: "Is everything traceable?",
    answer: "Yes. FlexiAnalyse keeps a full audit trail (who asked what, which query ran, and when) across your organisation, with strict multi-tenant isolation and role-scoped access."
  },
  {
    question: "How do I get started?",
    answer: "Create an account, connect a database (a pre-save connection test confirms it works), and start asking questions in plain language. No credit card required to try it."
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