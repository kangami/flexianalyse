import React from 'react';
import { Star, Quote } from 'lucide-react';

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
    <section className="py-14 sm:py-18 bg-gradient-to-br from-gray-50 to-white overflow-hidden">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16 sm:mb-20">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-gray-900 leading-tight mb-4">
            What Our Users Say
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Hear directly from the leaders and innovators who are transforming their operations with FlexiAnalyse.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 auto-rows-fr">
          {testimonials.map((testimonial, index) => (
            <div
              key={index}
              className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 flex flex-col justify-between border border-gray-100"
            >
              <div>
                <div className="flex items-center mb-4">
                  <Quote className="text-indigo-400 w-8 h-8 mr-2 opacity-75" />
                  <div className="flex text-yellow-500">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <Star key={i} className="w-5 h-5 fill-yellow-500 stroke-yellow-500" />
                    ))}
                  </div>
                </div>
                <p className="text-gray-800 text-lg italic mb-6 leading-relaxed">
                  "{testimonial.quote}"
                </p>
              </div>
              <div className="flex items-center mt-auto pt-4 border-t border-gray-50">
                <div className="flex-shrink-0 h-14 w-14 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xl uppercase ring-2 ring-indigo-300 ring-opacity-50">
                  {testimonial.name.split(' ').map(n => n[0]).join('')}
                </div>
                <div className="ml-4">
                  <p className="text-xl font-bold text-gray-900">{testimonial.name}</p>
                  <p className="text-indigo-600 text-md">{testimonial.title}</p>
                  <p className="text-gray-500 text-sm">{testimonial.company}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-20 text-center">
          <p className="text-gray-700 text-xl font-medium mb-3">Join thousands of satisfied customers</p>
          <p className="text-indigo-700 text-2xl font-bold">Trusted by <span className="text-indigo-500">5,000+</span> businesses worldwide</p>
        </div>
      </div>
    </section>
  );
};

export default TestimonialsSection;
