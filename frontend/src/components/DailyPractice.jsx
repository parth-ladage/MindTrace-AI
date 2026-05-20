import React, { useState } from 'react';
import { ChevronLeft, MessageCircle, Star, CheckCircle2, Shield, Heart, Sparkles } from 'lucide-react';

const DailyPractice = ({ onBack }) => {
  const [completed, setCompleted] = useState([]);

  const practices = [
    { 
      id: 'gratitude', 
      title: 'Daily Gratitude', 
      desc: 'List 3 specific things you are grateful for today.', 
      icon: <Heart className="w-5 h-5 text-pink-500" />,
      points: 10
    },
    { 
      id: 'presence', 
      title: 'Anchor Presence', 
      desc: 'Close your eyes and name 3 distinct sounds in your environment.', 
      icon: <Shield className="w-5 h-5 text-indigo-500" />,
      points: 15
    },
    { 
      id: 'reflection', 
      title: 'Daily Echo', 
      desc: 'Identify one choice you made today that aligns with your core values.', 
      icon: <Star className="w-5 h-5 text-amber-500" />,
      points: 20
    }
  ];

  const toggleComplete = (id) => {
    setCompleted(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  return (
    <div className="max-w-4xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-muted hover:text-foreground transition-colors group"
        >
          <ChevronLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
          <span className="text-[10px] font-black tracking-widest uppercase">Back to Control</span>
        </button>
        <div className="flex items-center gap-4">
          <div className="px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
            <span className="text-indigo-400 text-[10px] font-black tracking-widest uppercase">Stability Gained: +{completed.length * 15}%</span>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-muted text-[10px] font-black tracking-[0.3em] uppercase mb-1">Active Optimization</h2>
        <h1 className="text-4xl font-black tracking-tight mb-8">Daily Neuro-Practices</h1>
        
        <div className="grid grid-cols-1 gap-6">
          {practices.map((practice) => (
            <div 
              key={practice.id}
              className={`obsidian-card group cursor-pointer transition-all duration-500 ${
                completed.includes(practice.id) ? 'opacity-60 border-emerald-500/30' : 'hover:border-white/20'
              }`}
              onClick={() => toggleComplete(practice.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex gap-6">
                  <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors ${
                    completed.includes(practice.id) ? 'bg-emerald-500/20' : 'bg-glass group-hover:bg-glass brightness-110'
                  }`}>
                    {completed.includes(practice.id) ? <CheckCircle2 className="w-6 h-6 text-emerald-500" /> : practice.icon}
                  </div>
                  <div>
                    <h3 className={`text-xl font-bold mb-2 ${completed.includes(practice.id) ? 'text-emerald-500 line-through' : 'text-foreground'}`}>
                      {practice.title}
                    </h3>
                    <p className="text-muted text-sm max-w-lg leading-relaxed">
                      {practice.desc}
                    </p>
                  </div>
                </div>
                <div className={`text-[10px] font-black tracking-widest uppercase px-3 py-1 rounded-full ${
                  completed.includes(practice.id) ? 'bg-emerald-500/10 text-emerald-500' : 'bg-glass text-muted'
                }`}>
                  {completed.includes(practice.id) ? 'Completed' : `+${practice.points} Stability`}
                </div>
              </div>
            </div>
          ))}
        </div>

        {completed.length === practices.length && (
          <div className="p-8 bg-emerald-500/10 border border-emerald-500/20 rounded-3xl text-center animate-in zoom-in duration-500">
            <Sparkles className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h3 className="text-2xl font-black text-emerald-500 mb-2">Practice Complete</h3>
            <p className="text-emerald-500/70 text-sm font-medium">Your mood stability has been optimized for the day.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DailyPractice;
