import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchTemplates, deleteTemplate, duplicateTemplate, toggleTemplateStar } from '../store/templateSlice';
import { useDebounce } from '../hooks/useDebounce';
import { formatRelativeTime } from '../utils/formatters';

export default function TemplatesPage() {
  const dispatch = useAppDispatch();
  const { templates, loading } = useAppSelector((state) => state.templates);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const debouncedSearch = useDebounce(search);

  useEffect(() => {
    dispatch(fetchTemplates({
      search: debouncedSearch || undefined,
      template_type: typeFilter || undefined,
    }));
  }, [dispatch, debouncedSearch, typeFilter]);

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Delete template "${name}"?`)) {
      await dispatch(deleteTemplate(id));
      toast.success('Template deleted');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Email Templates</h1>
          <p className="text-gray-500 mt-1">Reusable templates for your campaigns</p>
        </div>
        <Link to="/templates/new/edit" className="btn-primary">New Template</Link>
      </div>

      <div className="flex gap-4 mb-6">
        <input type="text" placeholder="Search templates..." value={search}
          onChange={(e) => setSearch(e.target.value)} className="input-field max-w-xs" />
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="input-field w-44">
          <option value="">All Types</option>
          <option value="custom">Custom</option>
          <option value="system">System</option>
          <option value="shared">Shared</option>
        </select>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-36 bg-gray-200 rounded-lg mb-4" />
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : templates.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No templates found.</p>
          <Link to="/templates/new/edit" className="text-primary-600 hover:underline text-sm mt-2 inline-block">Create your first template</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {templates.map((template) => (
            <div key={template.id} className="card hover:shadow-md transition-shadow group">
              {/* Thumbnail */}
              <div className="h-36 bg-gray-100 rounded-lg mb-4 flex items-center justify-center overflow-hidden">
                {template.thumbnail ? (
                  <img src={template.thumbnail} alt={template.name} className="w-full h-full object-cover" />
                ) : (
                  <svg className="w-12 h-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                )}
              </div>

              <div className="flex items-start justify-between">
                <div>
                  <Link to={`/templates/${template.id}/edit`} className="font-medium text-gray-900 group-hover:text-primary-600">
                    {template.name}
                  </Link>
                  <p className="text-xs text-gray-500 mt-1">{formatRelativeTime(template.updated_at)}</p>
                </div>
                <button onClick={() => dispatch(toggleTemplateStar(template.id))}
                  className={`p-1 rounded ${template.is_starred ? 'text-yellow-500' : 'text-gray-300 hover:text-yellow-400'}`}
                >
                  <svg className="w-5 h-5" fill={template.is_starred ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                </button>
              </div>

              <div className="flex gap-2 mt-3">
                <span className={`badge ${template.template_type === 'system' ? 'badge-info' : 'badge-gray'}`}>
                  {template.template_type}
                </span>
                {template.usage_count > 0 && (
                  <span className="text-xs text-gray-400">Used {template.usage_count}x</span>
                )}
              </div>

              <div className="flex gap-2 mt-4 pt-3 border-t border-gray-100">
                <Link to={`/templates/${template.id}/edit`} className="text-sm text-gray-500 hover:text-primary-600">Edit</Link>
                <button onClick={() => dispatch(duplicateTemplate(template.id)).then(() => toast.success('Duplicated'))} className="text-sm text-gray-500 hover:text-primary-600">Duplicate</button>
                <button onClick={() => handleDelete(template.id, template.name)} className="text-sm text-gray-500 hover:text-red-600 ml-auto">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
