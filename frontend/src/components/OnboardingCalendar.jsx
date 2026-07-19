import React, { useState, useEffect } from 'react';

export default function OnboardingCalendar() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeDay, setActiveDay] = useState(new Date().getDay());
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
    { name: 'Mon', index: 1, isDispatch: true, title: 'Briefing Dispatch', desc: 'The compiled 3-minute markdown intelligence briefing hits your inbox at 9:00 AM.' },
    { name: 'Tue', index: 2, isDispatch: false, title: 'Scouting Feeds', desc: 'AI agents scan Hacker News and GitHub to collect raw trending signals.' },
    { name: 'Wed', index: 3, isDispatch: true, title: 'Briefing Dispatch', desc: 'The mid-week briefing is compiled, vetted, and dispatched to readers.' },
    { name: 'Thu', index: 4, isDispatch: false, title: 'Scouting Feeds', desc: 'AI agents filter duplication, check library readmes, and test raw candidates.' },
    { name: 'Fri', index: 5, isDispatch: true, title: 'Briefing Dispatch', desc: 'The weekend briefing hits your inbox, focusing on local dev tools and home setups.' },
    { name: 'Sat', index: 6, isDispatch: false, title: 'Web Scraping', desc: 'Scraper nodes extract engineering guides and package releases.' },
    { name: 'Sun', index: 0, isDispatch: false, title: 'Queue Run', desc: 'Agents run validation checks and queue up the Monday morning release payload.' }
  ];

  const todayIndex = currentTime.getDay();
  const selectedDayInfo = daysOfWeek.find(d => d.index === activeDay) || daysOfWeek[0];

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
    <div className="calendar-widget">
      <div className="calendar-grid-layout">
        
        {/* Left Column: Interactive Dials & Details */}
        <div className="calendar-left-col">
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
              <p className="calendar-subtitle">Click a day to view the curation cycle actions</p>
            </div>
          </div>

          <div className="calendar-week-grid">
            {daysOfWeek.map((day) => {
              const isToday = day.index === todayIndex;
              const isSelected = day.index === activeDay;
              return (
                <div 
                  key={day.name} 
                  className={`calendar-day-card ${day.isDispatch ? 'dispatch-day' : 'scouting-day'} ${isToday ? 'today-active' : ''} ${isSelected ? 'selected-day' : ''}`}
                  onClick={() => setActiveDay(day.index)}
                >
                  <span className="day-name">{day.name}</span>
                  <span className="day-status-dot"></span>
                </div>
              );
            })}
          </div>

          {/* Selected Day Details Panel */}
          {selectedDayInfo && (
            <div className="calendar-day-details animate-fade-in" style={{ '--accent-color': selectedDayInfo.isDispatch ? '#10b981' : '#f97316' }}>
              <div className="details-header">
                <span className="details-badge" style={{ 
                  backgroundColor: selectedDayInfo.isDispatch ? 'rgba(16, 185, 129, 0.1)' : 'rgba(249, 115, 22, 0.1)', 
                  color: selectedDayInfo.isDispatch ? '#10b981' : '#f97316',
                  border: `1px solid ${selectedDayInfo.isDispatch ? 'rgba(16, 185, 129, 0.2)' : 'rgba(249, 115, 22, 0.2)'}`
                }}>
                  {selectedDayInfo.isDispatch ? 'Dispatch' : 'Scouting'}
                </span>
                <h4>{selectedDayInfo.title}</h4>
              </div>
              <p className="details-desc">{selectedDayInfo.desc}</p>
            </div>
          )}
        </div>

        {/* Right Column: Countdown Timer & Onboarding Guide */}
        <div className="calendar-right-col">
          {nextDispatch && (
            <div className="calendar-countdown-section">
              <div className="countdown-item">
                <span className="countdown-label">NEXT DISPATCH:</span>
                <span className="countdown-value-date">{formatNextDate()}</span>
              </div>
              <div className="countdown-timer">
                <span className="countdown-label">COUNTDOWN:</span>
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

      </div>
    </div>
  );
}
