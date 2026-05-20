import React from 'react';
import { Eye, Volume2, FileText, Activity } from 'lucide-react';

/**
 * MultiModalCorrelation
 * 
 * Displays a side-by-side comparison of emotion readings from
 * different input sources (text, voice, webcam) to show
 * multi-modal correlation in the dashboard.
 */
const MultiModalCorrelation = ({ textEmotion, voiceEmotion, faceEmotion }) => {
  const sources = [
    { 
      label: 'Text Analysis', 
      icon: FileText, 
      data: textEmotion,
      color: 'indigo',
      gradient: 'from-indigo-500/20 to-indigo-600/5'
    },
    { 
      label: 'Voice Analysis', 
      icon: Volume2, 
      data: voiceEmotion,
      color: 'emerald',
      gradient: 'from-emerald-500/20 to-emerald-600/5'
    },
    { 
      label: 'Facial Analysis', 
      icon: Eye, 
      data: faceEmotion,
      color: 'purple',
      gradient: 'from-purple-500/20 to-purple-600/5'
    }
  ];

  const colorMap = {
    indigo: { text: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20', bar: 'bg-indigo-500' },
    emerald: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', bar: 'bg-emerald-500' },
    purple: { text: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20', bar: 'bg-purple-500' }
  };

  const hasAnyData = textEmotion || voiceEmotion || faceEmotion;

  if (!hasAnyData) return null;

  // Calculate agreement score
  const activeEmotions = [textEmotion, voiceEmotion, faceEmotion]
    .filter(Boolean)
    .map(d => d.emotion?.toLowerCase());
  
  const agreement = activeEmotions.length >= 2 
    ? activeEmotions.every(e => e === activeEmotions[0]) 
      ? 'High' 
      : 'Mixed'
    : 'N/A';

  const agreementColor = agreement === 'High' ? 'text-emerald-400' : agreement === 'Mixed' ? 'text-yellow-400' : 'text-muted';

  return (
    <div className="bg-glass border border-borderglass rounded-2xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-black tracking-widest uppercase text-foreground">Multi-Modal Correlation</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold tracking-widest uppercase text-muted">Agreement:</span>
          <span className={`text-[10px] font-black tracking-widest uppercase ${agreementColor}`}>{agreement}</span>
        </div>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {sources.map((source, i) => {
          const Icon = source.icon;
          const colors = colorMap[source.color];
          const data = source.data;

          return (
            <div 
              key={i} 
              className={`p-4 rounded-xl border bg-gradient-to-br ${source.gradient} ${
                data ? colors.border : 'border-borderglass opacity-40'
              }`}
            >
              <div className="flex items-center gap-2 mb-3">
                <div className={`p-1.5 rounded-lg ${colors.bg}`}>
                  <Icon className={`w-4 h-4 ${colors.text}`} />
                </div>
                <span className={`text-[10px] font-black tracking-widest uppercase ${colors.text}`}>
                  {source.label}
                </span>
              </div>

              {data ? (
                <div className="space-y-2">
                  <p className="text-lg font-black text-foreground capitalize">{data.emotion}</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${colors.bar} transition-all duration-500`}
                        style={{ width: `${Math.round((data.intensity || 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-bold text-muted tabular-nums">
                      {Math.round((data.intensity || 0) * 100)}%
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted italic">Not active</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MultiModalCorrelation;
