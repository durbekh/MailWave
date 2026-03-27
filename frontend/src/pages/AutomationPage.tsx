import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchWorkflows, deleteWorkflow, activateWorkflow, pauseWorkflow } from '../store/automationSlice';
import { formatNumber, formatPercent, formatRelativeTime, getStatusColor } from '../utils/formatters';

export default function AutomationPage() {
  const dispatch = useAppDispatch();
  const { workflows, loading } = useAppSelector((state) => state.automation);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    dispatch(fetchWorkflows({ status: statusFilter || undefined }));
  }, [dispatch, statusFilter]);

  const handleActivate = async (id: string) => {
    try {
      await dispatch(activateWorkflow(id)).unwrap();
      toast.success('Automation activated');
    } catch {
      toast.error('Failed to activate automation');
    }
  };

  const handlePause = async (id: string) => {
    await dispatch(pauseWorkflow(id));
    toast.success('Automation paused');
  };

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Delete automation "${name}"?`)) {
      await dispatch(deleteWorkflow(id));
      toast.success('Automation deleted');
    }
  };

  const triggerLabels: Record<string, string> = {
    subscription: 'Subscriber joins list',
    tag_added: 'Tag added',
    form_submit: 'Form submitted',
    date_field: 'Date-based',
    api_event: 'API event',
    manual: 'Manual enrollment',
    campaign_activity: 'Campaign activity',
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Automation</h1>
          <p className="text-gray-500 mt-1">Automated email sequences and workflows</p>
        </div>
        <Link to="/automation/new" className="btn-primary">New Automation</Link>
      </div>

      <div className="flex gap-4 mb-6">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field w-44">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-48 mb-3" />
              <div className="h-4 bg-gray-100 rounded w-96 mb-4" />
              <div className="flex gap-6">
                <div className="h-4 bg-gray-200 rounded w-20" />
                <div className="h-4 bg-gray-200 rounded w-20" />
                <div className="h-4 bg-gray-200 rounded w-20" />
              </div>
            </div>
          ))}
        </div>
      ) : workflows.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No automations found.</p>
          <Link to="/automation/new" className="text-primary-600 hover:underline text-sm mt-2 inline-block">
            Create your first automation
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {workflows.map((workflow) => (
            <div key={workflow.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <Link to={`/automation/${workflow.id}/edit`} className="text-lg font-semibold text-gray-900 hover:text-primary-600">
                      {workflow.name}
                    </Link>
                    <span className={`badge ${getStatusColor(workflow.status)}`}>{workflow.status}</span>
                  </div>
                  {workflow.description && (
                    <p className="text-sm text-gray-500 mt-1">{workflow.description}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Trigger: {triggerLabels[workflow.trigger_type] || workflow.trigger_type}
                    {' | '}{workflow.step_count} steps
                    {' | '}Updated {formatRelativeTime(workflow.updated_at)}
                  </p>
                </div>

                <div className="flex gap-2">
                  {workflow.status === 'draft' || workflow.status === 'paused' ? (
                    <button onClick={() => handleActivate(workflow.id)} className="btn-primary text-sm py-1.5 px-3">Activate</button>
                  ) : workflow.status === 'active' ? (
                    <button onClick={() => handlePause(workflow.id)} className="btn-secondary text-sm py-1.5 px-3">Pause</button>
                  ) : null}
                  <button onClick={() => handleDelete(workflow.id, workflow.name)} className="text-sm text-gray-400 hover:text-red-600 px-2">Delete</button>
                </div>
              </div>

              {/* Stats bar */}
              <div className="flex gap-8 mt-4 pt-4 border-t border-gray-100">
                <div>
                  <p className="text-xs text-gray-500">Enrolled</p>
                  <p className="text-sm font-semibold text-gray-900">{formatNumber(workflow.total_enrolled)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Active</p>
                  <p className="text-sm font-semibold text-blue-600">{formatNumber(workflow.currently_active)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Completed</p>
                  <p className="text-sm font-semibold text-green-600">{formatNumber(workflow.total_completed)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Conversion</p>
                  <p className="text-sm font-semibold text-purple-600">{formatPercent(workflow.conversion_rate)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
