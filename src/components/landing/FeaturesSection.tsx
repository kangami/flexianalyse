import React from 'react';
import { CheckCircle2, Database, FileText, ShieldCheck, Users } from 'lucide-react';

const FeaturesSection: React.FC = () => {
  const features = [
    {
      icon: <CheckCircle2 className="w-8 h-8 text-blue-500" />,
      title: "AI-Powered Analysis",
      description: "Leverage cutting-edge AI models for deep insights and predictive analytics."
    },
    {
      icon: <Database className="w-8 h-8 text-blue-500" />,
      title: "Multi-Platform Support",
      description: "Works seamlessly across devices, integrations, and cloud platforms."
    },
    {
      icon: <FileText className="w-8 h-8 text-blue-500" />,
      title: "Real-Time Updates",
      description: "Get instant results with live data processing and notifications."
    },
    {
      icon: <Users className="w-8 h-8 text-blue-500" />,
      title: "User-Friendly",
      description: "Intuitive interface designed for all skill levels, from beginners to experts."
    },
    {
      icon: <ShieldCheck className="w-8 h-8 text-blue-500" />,
      title: "Security-First",
      description: "Enterprise-grade encryption and compliance to protect your data."
    }
  ];

  return (
    <section className="py-20 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-16">
          Why Choose FlexiAnalyse?
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
          {features.map((feature, index) => (
            <div key={index} className="bg-gray-50 p-8 rounded-xl text-center hover:shadow-lg transition-shadow">
              <div className="mb-6">{feature.icon}</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">{feature.title}</h3>
              <p className="text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;