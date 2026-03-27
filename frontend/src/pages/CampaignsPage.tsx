import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchCampaigns, deleteCampaign, duplicateCampaign } from '../store/campaignSlice';
import { useDebounce } from '../hooks/useDebounce';
import { formatDate, formatNumber, formatPercent, getStatusColor } from '../utils/formatters';

export default function CampaignsPage() {
  const dispatch = useAppDispatch();
  const { campaigns, totalCount, loading } = useAppSelector((state) => state.campaigns);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search);

  useEffect(() => {
    dispatch(fetchCampaigns({ page, status: statusFilter || undefined, search: debouncedSearch || undefined }));
  }, [dispatch, page, statusFilter, debouncedSearch]);

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete "${name}"?`)) {
      await dispatch(deleteCampaign(id));
      toast.success('Campaign deleted');
    }
  };

  const handleDuplicate = async (id: string) => {
    await dispatch(duplicateCampaign(id));
    toast.success('Campaign duplicated');
  };

  const statuses = ['', 'draft', 'scheduled', 'sending', 'sent', 'paused', 'cancelled', 'failed'];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
          <p className="text-gray-500 mt-1">{formatNumber(totalCount)} total campaigns</p>
        </div>
        <Link to="/campaigns/new" className="btn-primary">New Campaign</Link>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search campaigns..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="input-field max-w-xs"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="input-field w-40"
        >
          {statuses.map((s) => (
            <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All Statuses'}</option>
          ))}
        </select>
      </div>

      {/* Campaign list */}
      <div className="card p-0 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaign</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sent</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Opens</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Clicks</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-40" /></td>
                  <td className="px-6 py-4"><div className="h-5 bg-gray-200 rounded w-16" /></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12 ml-auto" /></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12 ml-auto" /></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-12 ml-auto" /></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24" /></td>
                  <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-16 ml-auto" /></td>
                </tr>
              ))
            ) : campaigns.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                  No campaigns found. <Link to="/campaigns/new" className="text-primary-600 hover:underline">Create one</Link>
                </td>
              </tr>
            ) : (
              campaigns.map((campaign) => (
                <tr key={campaign.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link to={`/campaigns/${campaign.id}/edit`} className="font-medium text-gray-900 hover:text-primary-600">
                      {campaign.name}
                    </Link>
                    <p className="text-sm text-gray-500 truncate max-w-xs">{campaign.subject}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`badge ${getStatusColor(campaign.status)}`}>{campaign.status}</span>
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-gray-700">{formatNumber(campaign.total_sent)}</td>
                  <td className="px-6 py-4 text-right text-sm text-gray-700">{formatPercent(campaign.open_rate)}</td>
                  <td className="px-6 py-4 text-right text-sm text-gray-700">{formatPercent(campaign.click_rate)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatDate(campaign.sent_at || campaign.created_at)}</td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button onClick={() => handleDuplicate(campaign.id)} className="text-gray-400 hover:text-gray-600 text-sm">Duplicate</button>
                    <button onClick={() => handleDelete(campaign.id, campaign.name)} className="text-gray-400 hover:text-red-600 text-sm">Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalCount > 25 && (
        <div className="flex justify-center gap-2 mt-6">
          <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="btn-secondary text-sm">Previous</button>
          <span className="px-4 py-2 text-sm text-gray-600">Page {page}</span>
          <button onClick={() => setPage(page + 1)} disabled={campaigns.length < 25} className="btn-secondary text-sm">Next</button>
        </div>
      )}
    </div>
  );
}
