import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchDashboard, fetchDailyStats } from '../store/analyticsSlice';
import { formatNumber, formatPercent } from '../utils/formatters';

export default function DashboardPage() {
  const dispatch = useAppDispatch();
  const { dashboard, dailyStats, loading } = useAppSelector((state) => state.analytics);

  useEffect(() => {
    dispatch(fetchDashboard());
    const end = new Date().toISOString().split('T')[0];
    const start = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
    dispatch(fetchDailyStats({ start_date: start, end_date: end }));
  }, [dispatch]);

  const statCards = dashboard
    ? [
        { label: 'Total Contacts', value: formatNumber(dashboard.total_contacts), change: `+${formatNumber(dashboard.contacts_added_this_month)} this month`, color: 'text-blue-600' },
        { label: 'Emails Sent', value: formatNumber(dashboard.emails_sent_this_month), change: 'This month', color: 'text-green-600' },
        { label: 'Avg. Open Rate', value: formatPercent(dashboard.average_open_rate), change: 'Last 20 campaigns', color: 'text-purple-600' },
        { label: 'Avg. Click Rate', value: formatPercent(dashboard.average_click_rate), change: 'Last 20 campaigns', color: 'text-orange-600' },
        { label: 'Active Automations', value: formatNumber(dashboard.active_automations), change: 'Running now', color: 'text-indigo-600' },
        { label: 'Campaigns Sent', value: formatNumber(dashboard.campaigns_sent_this_month), change: 'This month', color: 'text-teal-600' },
      ]
    : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Overview of your email marketing performance</p>
        </div>
        <Link to="/campaigns/new" className="btn-primary">
          New Campaign
        </Link>
      </div>

      {/* Stat Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="stat-card animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-3" />
              <div className="h-8 bg-gray-200 rounded w-16 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-32" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
          {statCards.map((card) => (
            <div key={card.label} className="stat-card">
              <p className="text-sm font-medium text-gray-500">{card.label}</p>
              <p className={`text-2xl font-bold mt-1 ${card.color}`}>{card.value}</p>
              <p className="text-xs text-gray-400 mt-1">{card.change}</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Email Activity (Last 30 Days)</h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailyStats}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(d: string) => d.slice(5)} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Area type="monotone" dataKey="emails_sent" stroke="#6366f1" fill="#e0e7ff" name="Sent" />
              <Area type="monotone" dataKey="unique_opens" stroke="#10b981" fill="#d1fae5" name="Opens" />
              <Area type="monotone" dataKey="unique_clicks" stroke="#f59e0b" fill="#fef3c7" name="Clicks" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Link to="/campaigns/new" className="card hover:shadow-md transition-shadow group">
          <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Create Campaign</h3>
          <p className="text-sm text-gray-500 mt-1">Design and send a new email campaign to your subscribers.</p>
        </Link>
        <Link to="/subscribers" className="card hover:shadow-md transition-shadow group">
          <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Manage Subscribers</h3>
          <p className="text-sm text-gray-500 mt-1">Import, organize, and segment your contact lists.</p>
        </Link>
        <Link to="/automation/new" className="card hover:shadow-md transition-shadow group">
          <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Build Automation</h3>
          <p className="text-sm text-gray-500 mt-1">Create automated email sequences and workflows.</p>
        </Link>
      </div>
    </div>
  );
}
