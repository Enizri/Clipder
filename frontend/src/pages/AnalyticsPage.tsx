import React from 'react';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard';

export const AnalyticsPage: React.FC = () => {
  return (
    <div id="analytics" className="view-section active">
      <AnalyticsDashboard />
    </div>
  );
};
