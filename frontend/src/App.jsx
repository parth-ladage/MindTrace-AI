import React from 'react';
import { Home, BookOpen, BarChart3, Settings as SettingsIcon, Brain, LogOut, X, Menu, MessageCircle, Sun, Moon } from 'lucide-react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import JournalInput from './components/JournalInput';
import EmotionHistory from './components/EmotionHistory';
import Settings from './components/Settings';
import DistressMode from './components/DistressMode';
import ErrorBoundary from './components/ErrorBoundary';
import JournalHistory from './components/JournalHistory';
import Onboarding from './components/Onboarding';
import BreathingSession from './components/BreathingSession';
import DailyPractice from './components/DailyPractice';
import Companion from './components/Companion';
import BackgroundEmotionTracker from './components/BackgroundEmotionTracker';
import FunnyVideoIntervention from './components/FunnyVideoIntervention';
import { EmotionWebSocket } from './utils/websocket';

// Main App Content
const AppContent = () => {
  const { user, token, isAuthenticated, logout, loading, refreshUser } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [distressMode, setDistressMode] = React.useState(false);
  const [distressData, setDistressData] = React.useState({});
  const [currentPage, setCurrentPage] = React.useState('dashboard');
  const [onboardingComplete, setOnboardingComplete] = React.useState(false);
  const [showFunnyVideo, setShowFunnyVideo] = React.useState(false);
  const [currentEmotionData, setCurrentEmotionData] = React.useState({ emotion: 'Neutral', intensity: 0, timestamp: new Date() });
  const [intervention, setIntervention] = React.useState({ active: false, videoUrl: '', videoId: '', isChannel: false });
  const [theme, setTheme] = React.useState(localStorage.getItem('theme') || 'dark');

  React.useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const [negativeStreak, setNegativeStreak] = React.useState(0);
  const negativeStartTimeRef = React.useRef(null);
  const SUSTAINED_NEGATIVE_THRESHOLD = 20000; // 20 seconds in ms
  const NEGATIVE_STREAK_THRESHOLD = 5; // consecutive negative detections before funny video popup

  // Local Mood Sync Listener (Zero Latency)
  React.useEffect(() => {
    const handleMoodUpdate = (e) => {
      const { emotion, intensity, timestamp } = e.detail;
      const formattedEmotion = emotion.charAt(0).toUpperCase() + emotion.slice(1);
      
      setCurrentEmotionData({ 
        emotion: formattedEmotion, 
        intensity, 
        timestamp: timestamp || new Date() 
      });

      // Sustained distress detection (20s window)
      const negativeList = ['Sadness', 'Sad', 'Anger', 'Fear', 'Frustration', 'Anxiety', 'Depressed', 'Lonely'];
      if (negativeList.includes(formattedEmotion)) {
        if (!negativeStartTimeRef.current) {
          negativeStartTimeRef.current = Date.now();
        } else {
          const elapsed = Date.now() - negativeStartTimeRef.current;
          if (elapsed >= SUSTAINED_NEGATIVE_THRESHOLD) {
            triggerIntervention(formattedEmotion);
            negativeStartTimeRef.current = null; // Reset after trigger
          }
        }
      } else {
        negativeStartTimeRef.current = null;
      }
    };

    const triggerIntervention = async (emotion) => {
      try {
        // Fetch personalized video from our new backend service
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/sos/suggest-video?emotion=${emotion}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
      
        if (data.video_url) {
          setIntervention({
            active: true,
            videoUrl: data.video_url,
            videoId: data.video_url.split('v=')[1]?.split('&')[0],
            isChannel: data.video_url.includes('@')
          });
        }
      } catch (err) {
        console.error('Failed to trigger intervention:', err);
        setShowFunnyVideo(true); // Fallback to internal modal
      }
    };

    window.addEventListener('mood-update', handleMoodUpdate);
    return () => window.removeEventListener('mood-update', handleMoodUpdate);
  }, []);

  // Browser Notification Permission
  React.useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Scheduled Reminder: Journal for Synthesis (at 9:30 PM)
  React.useEffect(() => {
    const checkReminder = () => {
      const now = new Date();
      if (now.getHours() === 21 && now.getMinutes() === 30) {
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Neural Synthesis Reminder", {
            body: "It's 9:30 PM. Complete your journal entry to generate today's emotional synthesis report.",
            icon: "/logo192.png"
          });
        }
      }
    };

    const timer = setInterval(checkReminder, 60000); // Every minute
    return () => clearInterval(timer);
  }, []);

  // WebSocket for real-time alerts (Global persistence)
  React.useEffect(() => {
    if (!isAuthenticated || !user) return;

    const ws = new EmotionWebSocket(user.id, token);
    ws.connect().then(() => {
      ws.subscribe((message) => {
        if (message.type === 'escalation_detected') {
          const { escalation_level, trigger_emotions } = message.data;
          const negativeEmotions = ['sadness', 'sad', 'anger', 'fear', 'frustration', 'anxiety', 'depressed'];
          const hasNegativeEmotion = trigger_emotions?.some(e => negativeEmotions.includes(e.toLowerCase()));

          if ((escalation_level === 'escalating' || escalation_level === 'critical') && hasNegativeEmotion) {
            setCurrentEmotionData({ 
              emotion: trigger_emotions[0], 
              intensity: 0.8, 
              timestamp: new Date() 
            });
            setShowFunnyVideo(true);

            // Notify user of escalation
            if (Notification.permission === "granted") {
              new Notification("Neural Alert", { body: `High ${trigger_emotions[0]} detected. Protocol recommended.` });
            }
          }
        } else if (message.type === 'emotion_detected') {
          console.log('[WebSocket] Live Emotion Update:', message.data);
          const { emotion, intensity } = message.data;
          const formattedEmotion = emotion.charAt(0).toUpperCase() + emotion.slice(1);
          
          setCurrentEmotionData({ 
            emotion: formattedEmotion, 
            intensity, 
            timestamp: new Date() 
          });

          // Immediate Streak Detection for Funny Video Pop-up
          const negativeList = ['Sadness', 'Sad', 'Anger', 'Fear', 'Frustration', 'Anxiety', 'Depressed'];
          if (negativeList.includes(formattedEmotion)) {
            setNegativeStreak(prev => {
              const newStreak = prev + 1;
              if (newStreak >= NEGATIVE_STREAK_THRESHOLD) {
                setShowFunnyVideo(true);
                return 0; // Reset after trigger
              }
              return newStreak;
            });
          } else if (formattedEmotion === 'Joy' || formattedEmotion === 'Calm') {
            setNegativeStreak(0); // Reset on positive emotion
          }
        }
      });
    }).catch(console.error);

    return () => ws.disconnect();
  }, [isAuthenticated, user, token]);

  // Check if onboarding is needed
  const needsOnboarding = isAuthenticated && !user?.guardian_email && !onboardingComplete;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#000000]">
        <div className="text-center">
          <div className="mb-4">
            <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mx-auto"></div>
          </div>
          <p className="text-gray-400 font-bold tracking-widest uppercase text-xs">Neural Sync...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  if (needsOnboarding) {
    return <Onboarding user={user} onComplete={async () => {
      await refreshUser();
      setOnboardingComplete(true);
    }} />;
  }

  const handleLogout = () => {
    logout();
  };

  const handleDistressAlert = (emotionData) => {
    if (emotionData.escalation_score >= 0.85) {
      setDistressData(emotionData);
      setDistressMode(true);
    }
  };

  const navigationItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'companion', label: 'AI Companion', icon: MessageCircle },
    { id: 'journal', label: 'Daily Journal', icon: BookOpen },
    { id: 'analytics', label: 'Insights', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-indigo-500/30 font-inter transition-colors duration-500">
      {/* Header */}
      <header className="bg-background/80 backdrop-blur-md border-b border-borderglass sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.5)] overflow-hidden">
                <img src="/logo.png" alt="MindTrace Logo" className="w-full h-full object-cover" />
              </div>
              <h1 className="text-xl font-black tracking-tighter text-foreground">MINDTRACE<span className="text-indigo-500">AI+</span></h1>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-2">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setCurrentPage(item.id)}
                    className={`px-5 py-2.5 rounded-2xl text-[10px] font-black tracking-[0.2em] uppercase transition-all duration-300 flex items-center gap-3 ${
                      currentPage === item.id
                        ? 'bg-glass text-foreground border border-borderglass shadow-lg'
                        : 'text-muted hover:text-foreground hover:bg-glass'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${currentPage === item.id ? 'text-indigo-500' : ''}`} />
                    {item.label}
                  </button>
                );
              })}
            </nav>

            {/* User Info & Theme Toggle */}
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="p-2 rounded-xl bg-glass border border-borderglass text-muted hover:text-foreground transition-all active:scale-95"
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              
              <div className="hidden sm:block text-right ml-2">
                <p className="text-sm font-bold text-foreground">{user?.full_name || user?.name || user?.email.split('@')[0]}</p>
                <div className="flex items-center justify-end gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                  <p className="text-[10px] font-black tracking-widest text-emerald-500 uppercase">Connected</p>
                </div>
              </div>
              {/* Mobile Menu Button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden w-11 h-11 bg-surface border border-borderglass flex items-center justify-center rounded-2xl text-muted"
              >
                {mobileMenuOpen ? (
                  <X className="w-6 h-6" />
                ) : (
                  <Menu className="w-6 h-6" />
                )}
              </button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <nav className="md:hidden pb-6 pt-2 space-y-2">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setCurrentPage(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full text-left px-5 py-4 rounded-2xl text-xs font-black tracking-widest uppercase transition-all flex items-center gap-4 ${
                      currentPage === item.id
                        ? 'bg-glass text-foreground border border-borderglass'
                        : 'text-muted'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${currentPage === item.id ? 'text-indigo-500' : ''}`} />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 lg:px-8 py-12">
        {currentPage === 'dashboard' && (
          <Dashboard 
            user={user}
            onDistressAlert={handleDistressAlert} 
            onNavigate={setCurrentPage} 
            currentMood={currentEmotionData}
          />
        )}
        {currentPage === 'companion' && (
          <Companion currentEmotionData={currentEmotionData} />
        )}
        {currentPage === 'journal' && (
          <JournalInput onDistressAlert={handleDistressAlert} />
        )}
        {currentPage === 'analytics' && (
          <JournalHistory />
        )}
        {currentPage === 'settings' && (
          <Settings user={user} onLogout={handleLogout} />
        )}
        {currentPage === 'breathing' && (
          <BreathingSession onBack={() => setCurrentPage('dashboard')} />
        )}
        {currentPage === 'practice' && (
          <DailyPractice onBack={() => setCurrentPage('dashboard')} />
        )}

      {/* Floating Action Button (Optional, can be used for manual distress trigger) */}
      <div className="fixed bottom-8 left-8 z-50">
        <button 
          onClick={() => setDistressMode(true)}
          className="w-14 h-14 bg-red-600 hover:bg-red-500 text-white rounded-full flex items-center justify-center shadow-[0_0_20px_rgba(220,38,38,0.5)] transition-all hover:scale-110"
          title="Manual Neural Alert"
        >
          <Brain size={24} />
        </button>
      </div>

      {/* Neural Intervention Widget (Ad-style Pop-up) */}
      {intervention.active && (
        <div className="fixed bottom-6 right-6 w-[320px] h-[200px] z-[9999] animate-in slide-in-from-right duration-500">
          <div className="relative w-full h-full bg-[#111] rounded-xl border border-white/10 shadow-2xl overflow-hidden group">
            {/* Header / Close */}
            <div className="absolute top-0 left-0 right-0 p-2 bg-gradient-to-b from-black/80 to-transparent z-10 flex justify-between items-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-[10px] font-bold tracking-widest text-indigo-400 ml-2">NEURAL RESET</span>
              <button 
                onClick={() => setIntervention({ ...intervention, active: false })}
                className="p-1 hover:bg-white/10 rounded-full text-white/50 hover:text-white transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            {/* Video Content */}
            {intervention.isChannel ? (
              <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-indigo-900/20 text-center">
                <p className="text-xs text-white/70 mb-3">Intervention Suggested</p>
                <a 
                  href={intervention.videoUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-[10px] font-bold tracking-wider transition-all"
                >
                  OPEN RESET CHANNEL
                </a>
              </div>
            ) : (
              <iframe 
                width="100%" 
                height="100%" 
                src={`https://www.youtube.com/embed/${intervention.videoId}?autoplay=1&modestbranding=1&controls=1`}
                frameBorder="0" 
                allow="autoplay; encrypted-media" 
                allowFullScreen
              ></iframe>
            )}
          </div>
        </div>
      )}

      {/* Distress Overlays */}
      {distressMode && (
        <DistressMode 
          data={distressData} 
          onClose={() => setDistressMode(false)} 
        />
      )}
      
      {showFunnyVideo && (
        <FunnyVideoIntervention 
          onClose={() => setShowFunnyVideo(false)}
          emotion={currentEmotionData.emotion}
        />
      )}
      </main>

      {/* Global Passive Tracking */}
      <BackgroundEmotionTracker enabled={user?.background_tracking_enabled} />
    </div>
  );
};

// Main App Component
const App = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <AppContent />
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
