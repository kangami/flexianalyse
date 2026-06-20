import React from 'react';

const testimonials = [
  {
    name: "Sarah Johnson",
    title: "CEO, HealthTech Solutions",
    company: "MedAI Inc.",
    rating: 5,
    quote: "FlexiAnalyse transformed our patient outcome predictions. The accuracy and speed are unmatched in the industry. Our team couldn't be happier with the results."
  },
  {
    name: "Michael Chen",
    title: "Chief Data Officer",
    company: "Global Retail Analytics",
    rating: 5,
    quote: "Since implementing FlexiAnalyse, we've seen a 30% increase in sales through personalized recommendations. The platform is intuitive and powerful."
  },
  {
    name: "Emily Rodriguez",
    title: "Director of Operations",
    company: "EcoManufacturing Corp.",
    rating: 5,
    quote: "FlexiAnalyse helped us predict equipment failures before they happened, saving us millions in downtime costs. It's a game-changer for our industry."
  }
];

const TestimonialsSection: React.FC = () => {
  return (
    <section className="py-20 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-16">
          What Our Users Say
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <div key={index} className="bg-gray-50 p-8 rounded-xl">
              <div className="flex items-center mb-4">
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-lg">★</span>
                  ))}
                </div>
              </div>
              <p className="text-gray-700 italic mb-6">
                "{testimonial.quote}"
              </p>
              <div className="flex items-center">
                <div className="flex-shrink-0 h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                  {testimonial.name.split(' ').map(n => n[0]).join('')}
                </div>
                <div className="ml-4">
                  <p className="text-lg font-semibold text-gray-900">{testimonial.name}</p>
                  <p className="text-gray-600">{testimonial.title}</p>
                  <p className="text-gray-500 text-sm">{testimonial.company}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-2">Join thousands of satisfied customers</p>
          <p className="text-blue-600 font-semibold">Trusted by 5,000+ businesses worldwide</p>
        </div>
      </div>
    </section>
  );
};

export default TestimonialsSection;