import { useEffect, useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchDashboard, fetchDailyStats } from '../store/analyticsSlice';
import { formatNumber, formatPercent } from '../utils/formatters';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function AnalyticsPage() {
  const dispatch = useAppDispatch();
  const { dashboard, dailyStats, loading } = useAppSelector((state) => state.analytics);
  const [dateRange, setDateRange] = useState(30);

  useEffect(() => {
    dispatch(fetchDashboard());
  }, [dispatch]);

  useEffect(() => {
    const end = new Date().toISOString().split('T')[0];
    const start = new Date(Date.now() - dateRange * 86400000).toISOString().split('T')[0];
    dispatch(fetchDailyStats({ start_date: start, end_date: end }));
  }, [dispatch, dateRange]);

  const engagementData = dashboard
    ? [
        { name: 'Opens', value: dashboard.average_open_rate },
        { name: 'Clicks', value: dashboard.average_click_rate },
        { name: 'Unread', value: Math.max(0, 100 - dashboard.average_open_rate) },
      ]
    : [];

  const growthData = dashboard
    ? [
        { name: 'Active', value: dashboard.active_contacts },
        { name: 'New (month)', value: dashboard.contacts_added_this_month },
        { name: 'Unsubscribed', value: dashboard.unsubscribes_this_month },
      ]
    : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Track your email marketing performance</p>
        </div>
        <select value={dateRange} onChange={(e) => setDateRange(Number(e.target.value))} className="input-field w-44">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* Key metrics */}
      {!loading && dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8">
          <div className="stat-card">
            <p className="text-sm text-gray-500">Emails Sent</p>
            <p className="text-2xl font-bold text-gray-900">{formatNumber(dashboard.emails_sent_this_month)}</p>
            <p className="text-xs text-gray-400">This month</p>
          </div>
          <div className="stat-card">
            <p className="text-sm text-gray-500">Avg. Open Rate</p>
            <p className="text-2xl font-bold text-green-600">{formatPercent(dashboard.average_open_rate)}</p>
            <p className="text-xs text-gray-400">Last 20 campaigns</p>
          </div>
          <div className="stat-card">
            <p className="text-sm text-gray-500">Avg. Click Rate</p>
            <p className="text-2xl font-bold text-blue-600">{formatPercent(dashboard.average_click_rate)}</p>
            <p className="text-xs text-gray-400">Last 20 campaigns</p>
          </div>
          <div className="stat-card">
            <p className="text-sm text-gray-500">Subscriber Growth</p>
            <p className="text-2xl font-bold text-purple-600">+{formatNumber(dashboard.contacts_added_this_month)}</p>
            <p className="text-xs text-gray-400">New this month</p>
          </div>
        </div>
      )}

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Daily sends/opens */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Email Activity</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="emails_sent" stroke="#6366f1" name="Sent" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="unique_opens" stroke="#10b981" name="Opens" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="unique_clicks" stroke="#f59e0b" name="Clicks" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bounce / unsubscribes */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Bounces & Unsubscribes</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="bounces" fill="#ef4444" name="Bounces" radius={[2, 2, 0, 0]} />
                <Bar dataKey="unsubscribes" fill="#f59e0b" name="Unsubscribes" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Engagement pie */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Average Engagement</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={engagementData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                  paddingAngle={3} dataKey="value" label={({ name, value }: { name: string; value: number }) => `${name}: ${value.toFixed(1)}%`}>
                  {engagementData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Subscriber growth */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscriber Overview</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={growthData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={100} />
                <Tooltip />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {growthData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
