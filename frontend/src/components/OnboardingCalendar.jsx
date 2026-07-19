import React, { useState, useEffect } from 'react';

export default function OnboardingCalendar() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [countdown, setCountdown] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 });
  const [nextDispatch, setNextDispatch] = useState(null);

  // Thrice weekly schedule: Monday (1), Wednesday (3), Friday (5) at 9:00 AM local time
  useEffect(() => {
    function calculateNextDispatch() {
      const now = new Date();
      const dispatchDays = [1, 3, 5]; // Mon, Wed, Fri
      const candidates = [];

      dispatchDays.forEach((dayOfWeek) => {
        let candidate = new Date(now);
        // Calculate difference in days to reach the next occurrence of dayOfWeek
        let diff = (dayOfWeek + 7 - now.getDay()) % 7;
        
        // If it is the dispatch day itself
        if (diff === 0) {
          // If we have already passed 9:00 AM, the next is next week
          const todayNineAM = new Date(now);
          todayNineAM.setHours(9, 0, 0, 0);
          if (now >= todayNineAM) {
            diff = 7;
          }
        }
        
        candidate.setDate(now.getDate() + diff);
        candidate.setHours(9, 0, 0, 0);
        candidates.push(candidate);
      });

      // Find the earliest candidate datetime
      candidates.sort((a, b) => a - b);
      return candidates[0];
    }

    const target = calculateNextDispatch();
    setNextDispatch(target);

    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(now);
      
      const diffMs = target - now;
      if (diffMs <= 0) {
        // Re-calculate if countdown reaches 0
        const newTarget = calculateNextDispatch();
        setNextDispatch(newTarget);
      } else {
        const totalSeconds = Math.floor(diffMs / 1000);
        const days = Math.floor(totalSeconds / (3600 * 24));
        const hours = Math.floor((totalSeconds % (3600 * 24)) / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        setCountdown({ days, hours, minutes, seconds });
      }
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const daysOfWeek = [
    { name: 'Mon', index: 1, isDispatch: true, desc: 'Briefing Dispatch' },
    { name: 'Tue', index: 2, isDispatch: false, desc: 'Scouting Ecosystem' },
    { name: 'Wed', index: 3, isDispatch: true, desc: 'Briefing Dispatch' },
    { name: 'Thu', index: 4, isDispatch: false, desc: 'Scouting Ecosystem' },
    { name: 'Fri', index: 5, isDispatch: true, desc: 'Briefing Dispatch' },
    { name: 'Sat', index: 6, isDispatch: false, desc: 'Web Scraping' },
    { name: 'Sun', index: 0, isDispatch: false, desc: 'Queue Run' }
  ];

  const todayIndex = currentTime.getDay();

  const formatNextDate = () => {
    if (!nextDispatch) return 'Calculating...';
    return nextDispatch.toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  return (
    <div className="calendar-widget glass-card">
      <div className="calendar-header">
        <span className="calendar-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="20" height="20" style={{ display: 'block' }}>
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </span>
        <div>
          <h4 className="calendar-title">Dispatch Schedule</h4>
          <p className="calendar-subtitle">How our curation cycle runs</p>
        </div>
      </div>

      <div className="calendar-week-grid">
        {daysOfWeek.map((day) => {
          const isToday = day.index === todayIndex;
          return (
            <div 
              key={day.name} 
              className={`calendar-day-card ${day.isDispatch ? 'dispatch-day' : 'scouting-day'} ${isToday ? 'today-active' : ''}`}
            >
              <span className="day-name">{day.name}</span>
              <span className="day-status-dot"></span>
              <span className="day-label-hover">{day.desc}</span>
            </div>
          );
        })}
      </div>

      {nextDispatch && (
        <div className="calendar-countdown-section">
          <div className="countdown-item">
            <span className="countdown-label">NEXT DROP ON:</span>
            <span className="countdown-value-date">{formatNextDate()}</span>
          </div>
          <div className="countdown-timer">
            <span className="countdown-label">TIME REMAINING:</span>
            <div className="timer-numbers">
              {countdown.days > 0 && (
                <>
                  <span className="time-part">{countdown.days}<small>d</small></span>
                  <span className="time-divider">:</span>
                </>
              )}
              <span className="time-part">{String(countdown.hours).padStart(2, '0')}<small>h</small></span>
              <span className="time-divider">:</span>
              <span className="time-part">{String(countdown.minutes).padStart(2, '0')}<small>m</small></span>
              <span className="time-divider">:</span>
              <span className="time-part-sec">{String(countdown.seconds).padStart(2, '0')}<small>s</small></span>
            </div>
          </div>
        </div>
      )}
      
      <div className="onboarding-guide-text">
        <p>
          <strong>First time reading?</strong> Every Monday, Wednesday, and Friday, our AI agents scan developer communities to bring you exactly 5 curated, practical tech updates. We strip out academic formulas and clickbait, leaving you with simple explanations and clear verdicts.
        </p>
      </div>
    </div>
  );
}
