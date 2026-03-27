import { useEffect, useState, FormEvent } from 'react';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchContacts, createContact, deleteContact, fetchLists, createList, fetchTags, bulkImportContacts } from '../store/contactSlice';
import { useDebounce } from '../hooks/useDebounce';
import { formatDate, formatNumber, formatPercent, getStatusColor } from '../utils/formatters';

type TabType = 'contacts' | 'lists' | 'import';

export default function SubscribersPage() {
  const dispatch = useAppDispatch();
  const { contacts, totalCount, lists, tags, loading } = useAppSelector((state) => state.contacts);
  const [tab, setTab] = useState<TabType>('contacts');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newContact, setNewContact] = useState({ email: '', first_name: '', last_name: '', company: '' });
  const [newListName, setNewListName] = useState('');
  const [importJson, setImportJson] = useState('');
  const debouncedSearch = useDebounce(search);

  useEffect(() => {
    dispatch(fetchContacts({ page, status: statusFilter || undefined, search: debouncedSearch || undefined }));
    dispatch(fetchLists());
    dispatch(fetchTags());
  }, [dispatch, page, statusFilter, debouncedSearch]);

  const handleAddContact = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await dispatch(createContact(newContact)).unwrap();
      toast.success('Contact added');
      setShowAddModal(false);
      setNewContact({ email: '', first_name: '', last_name: '', company: '' });
    } catch {
      toast.error('Failed to add contact');
    }
  };

  const handleCreateList = async (e: FormEvent) => {
    e.preventDefault();
    if (!newListName.trim()) return;
    await dispatch(createList({ name: newListName }));
    toast.success('List created');
    setNewListName('');
  };

  const handleBulkImport = async () => {
    try {
      const parsed = JSON.parse(importJson);
      const result = await dispatch(bulkImportContacts({ contacts: parsed })).unwrap();
      toast.success(`Imported: ${result.created} created, ${result.updated} updated, ${result.skipped} skipped`);
      setImportJson('');
      dispatch(fetchContacts({ page: 1 }));
    } catch {
      toast.error('Invalid JSON or import failed');
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Delete this contact?')) {
      await dispatch(deleteContact(id));
      toast.success('Contact deleted');
    }
  };

  const tabs: { key: TabType; label: string }[] = [
    { key: 'contacts', label: `Contacts (${formatNumber(totalCount)})` },
    { key: 'lists', label: `Lists (${lists.length})` },
    { key: 'import', label: 'Import' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Subscribers</h1>
        <button onClick={() => setShowAddModal(true)} className="btn-primary">Add Contact</button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${tab === t.key ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >{t.label}</button>
        ))}
      </div>

      {/* Contacts Tab */}
      {tab === 'contacts' && (
        <>
          <div className="flex gap-4 mb-4">
            <input type="text" placeholder="Search contacts..." value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="input-field max-w-xs" />
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="input-field w-44">
              <option value="">All Statuses</option>
              <option value="subscribed">Subscribed</option>
              <option value="unsubscribed">Unsubscribed</option>
              <option value="bounced">Bounced</option>
            </select>
          </div>

          <div className="card p-0 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Engagement</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Added</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      {[...Array(6)].map((_, j) => (
                        <td key={j} className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-20" /></td>
                      ))}
                    </tr>
                  ))
                ) : contacts.length === 0 ? (
                  <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500">No contacts found.</td></tr>
                ) : (
                  contacts.map((contact) => (
                    <tr key={contact.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{contact.email}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">{contact.full_name || '--'}</td>
                      <td className="px-6 py-4"><span className={`badge ${getStatusColor(contact.status)}`}>{contact.status}</span></td>
                      <td className="px-6 py-4 text-right text-sm text-gray-700">{formatPercent(contact.engagement_rate)}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">{formatDate(contact.created_at)}</td>
                      <td className="px-6 py-4 text-right">
                        <button onClick={() => handleDelete(contact.id)} className="text-sm text-gray-400 hover:text-red-600">Delete</button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalCount > 25 && (
            <div className="flex justify-center gap-2 mt-6">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="btn-secondary text-sm">Previous</button>
              <span className="px-4 py-2 text-sm text-gray-600">Page {page}</span>
              <button onClick={() => setPage(page + 1)} disabled={contacts.length < 25} className="btn-secondary text-sm">Next</button>
            </div>
          )}
        </>
      )}

      {/* Lists Tab */}
      {tab === 'lists' && (
        <div>
          <form onSubmit={handleCreateList} className="flex gap-3 mb-6">
            <input type="text" value={newListName} onChange={(e) => setNewListName(e.target.value)} className="input-field max-w-xs" placeholder="New list name" />
            <button type="submit" className="btn-primary">Create List</button>
          </form>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {lists.map((list) => (
              <div key={list.id} className="card">
                <h3 className="font-semibold text-gray-900">{list.name}</h3>
                <p className="text-sm text-gray-500 mt-1">{list.description || 'No description'}</p>
                <div className="flex gap-4 mt-3 text-sm">
                  <span className="text-green-600">{formatNumber(list.contact_count)} subscribed</span>
                  <span className="text-red-500">{formatNumber(list.unsubscribed_count)} unsubscribed</span>
                </div>
                <p className="text-xs text-gray-400 mt-2">Created {formatDate(list.created_at)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Import Tab */}
      {tab === 'import' && (
        <div className="card max-w-2xl">
          <h2 className="font-semibold text-gray-900 mb-4">Bulk Import Contacts</h2>
          <p className="text-sm text-gray-500 mb-4">
            Paste JSON array of contacts. Each object should have: email, first_name, last_name, company (optional).
          </p>
          <textarea value={importJson} onChange={(e) => setImportJson(e.target.value)} className="input-field font-mono text-sm" rows={12}
            placeholder={'[\n  {"email": "john@example.com", "first_name": "John", "last_name": "Doe"},\n  {"email": "jane@example.com", "first_name": "Jane", "last_name": "Smith"}\n]'} />
          <button onClick={handleBulkImport} className="btn-primary mt-4">Import Contacts</button>
        </div>
      )}

      {/* Add Contact Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Contact</h2>
            <form onSubmit={handleAddContact} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" value={newContact.email} onChange={(e) => setNewContact((p) => ({ ...p, email: e.target.value }))} className="input-field" required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                  <input type="text" value={newContact.first_name} onChange={(e) => setNewContact((p) => ({ ...p, first_name: e.target.value }))} className="input-field" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                  <input type="text" value={newContact.last_name} onChange={(e) => setNewContact((p) => ({ ...p, last_name: e.target.value }))} className="input-field" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                <input type="text" value={newContact.company} onChange={(e) => setNewContact((p) => ({ ...p, company: e.target.value }))} className="input-field" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowAddModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Add Contact</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
