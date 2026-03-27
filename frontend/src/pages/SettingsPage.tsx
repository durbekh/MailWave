import { useEffect, useState, FormEvent } from 'react';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchCurrentUser } from '../store/authSlice';
import api from '../utils/api';
import { formatNumber } from '../utils/formatters';

type SettingsTab = 'profile' | 'organization' | 'billing' | 'team';

export default function SettingsPage() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const [tab, setTab] = useState<SettingsTab>('profile');
  const [profileForm, setProfileForm] = useState({
    first_name: '', last_name: '', phone: '', timezone: 'UTC',
  });
  const [orgForm, setOrgForm] = useState({
    name: '', website: '', default_from_email: '', default_from_name: '', default_reply_to: '',
  });
  const [passwordForm, setPasswordForm] = useState({
    old_password: '', new_password: '', new_password_confirm: '',
  });
  const [members, setMembers] = useState<Array<{
    id: string; email: string; full_name: string; role: string;
  }>>([]);

  useEffect(() => {
    if (user) {
      setProfileForm({
        first_name: user.first_name, last_name: user.last_name,
        phone: user.phone || '', timezone: user.timezone,
      });
    }
  }, [user]);

  useEffect(() => {
    if (tab === 'organization' && user?.organization_details) {
      const org = user.organization_details;
      setOrgForm({
        name: org.name, website: org.website || '',
        default_from_email: org.default_from_email || '',
        default_from_name: org.default_from_name || '',
        default_reply_to: org.default_reply_to || '',
      });
    }
    if (tab === 'team') {
      api.get('/auth/organization/members/').then((res) => setMembers(res.data));
    }
  }, [tab, user]);

  const handleUpdateProfile = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.patch('/auth/me/', profileForm);
      dispatch(fetchCurrentUser());
      toast.success('Profile updated');
    } catch {
      toast.error('Failed to update profile');
    }
  };

  const handleUpdateOrg = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.patch('/auth/organization/current/', orgForm);
      dispatch(fetchCurrentUser());
      toast.success('Organization updated');
    } catch {
      toast.error('Failed to update organization');
    }
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/auth/change-password/', passwordForm);
      toast.success('Password changed');
      setPasswordForm({ old_password: '', new_password: '', new_password_confirm: '' });
    } catch {
      toast.error('Failed to change password');
    }
  };

  const tabs: { key: SettingsTab; label: string }[] = [
    { key: 'profile', label: 'Profile' },
    { key: 'organization', label: 'Organization' },
    { key: 'billing', label: 'Billing & Plan' },
    { key: 'team', label: 'Team Members' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${tab === t.key ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >{t.label}</button>
        ))}
      </div>

      {/* Profile */}
      {tab === 'profile' && (
        <div className="max-w-2xl space-y-8">
          <form onSubmit={handleUpdateProfile} className="card space-y-4">
            <h2 className="font-semibold text-gray-900">Personal Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                <input type="text" value={profileForm.first_name} onChange={(e) => setProfileForm((p) => ({ ...p, first_name: e.target.value }))} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                <input type="text" value={profileForm.last_name} onChange={(e) => setProfileForm((p) => ({ ...p, last_name: e.target.value }))} className="input-field" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input type="text" value={profileForm.phone} onChange={(e) => setProfileForm((p) => ({ ...p, phone: e.target.value }))} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
              <select value={profileForm.timezone} onChange={(e) => setProfileForm((p) => ({ ...p, timezone: e.target.value }))} className="input-field">
                <option value="UTC">UTC</option>
                <option value="US/Eastern">US/Eastern</option>
                <option value="US/Central">US/Central</option>
                <option value="US/Mountain">US/Mountain</option>
                <option value="US/Pacific">US/Pacific</option>
                <option value="Europe/London">Europe/London</option>
                <option value="Europe/Berlin">Europe/Berlin</option>
                <option value="Asia/Tokyo">Asia/Tokyo</option>
              </select>
            </div>
            <button type="submit" className="btn-primary">Save Changes</button>
          </form>

          <form onSubmit={handleChangePassword} className="card space-y-4">
            <h2 className="font-semibold text-gray-900">Change Password</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
              <input type="password" value={passwordForm.old_password} onChange={(e) => setPasswordForm((p) => ({ ...p, old_password: e.target.value }))} className="input-field" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
              <input type="password" value={passwordForm.new_password} onChange={(e) => setPasswordForm((p) => ({ ...p, new_password: e.target.value }))} className="input-field" required minLength={10} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
              <input type="password" value={passwordForm.new_password_confirm} onChange={(e) => setPasswordForm((p) => ({ ...p, new_password_confirm: e.target.value }))} className="input-field" required />
            </div>
            <button type="submit" className="btn-primary">Change Password</button>
          </form>
        </div>
      )}

      {/* Organization */}
      {tab === 'organization' && (
        <form onSubmit={handleUpdateOrg} className="card max-w-2xl space-y-4">
          <h2 className="font-semibold text-gray-900">Organization Settings</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
            <input type="text" value={orgForm.name} onChange={(e) => setOrgForm((p) => ({ ...p, name: e.target.value }))} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
            <input type="url" value={orgForm.website} onChange={(e) => setOrgForm((p) => ({ ...p, website: e.target.value }))} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default From Email</label>
            <input type="email" value={orgForm.default_from_email} onChange={(e) => setOrgForm((p) => ({ ...p, default_from_email: e.target.value }))} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default From Name</label>
            <input type="text" value={orgForm.default_from_name} onChange={(e) => setOrgForm((p) => ({ ...p, default_from_name: e.target.value }))} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Reply-To</label>
            <input type="email" value={orgForm.default_reply_to} onChange={(e) => setOrgForm((p) => ({ ...p, default_reply_to: e.target.value }))} className="input-field" />
          </div>
          <button type="submit" className="btn-primary">Save Organization</button>
        </form>
      )}

      {/* Billing */}
      {tab === 'billing' && user?.organization_details && (
        <div className="max-w-2xl">
          <div className="card mb-6">
            <h2 className="font-semibold text-gray-900 mb-4">Current Plan</h2>
            <div className="flex items-center justify-between p-4 bg-primary-50 rounded-lg">
              <div>
                <p className="text-lg font-bold text-primary-700">
                  {user.organization_details.plan_details?.name || 'Free'} Plan
                </p>
                <p className="text-sm text-primary-600">
                  {formatNumber(user.organization_details.plan_details?.monthly_email_limit || 0)} emails/month
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-primary-700">
                  ${user.organization_details.plan_details?.price_monthly || '0'}
                </p>
                <p className="text-xs text-primary-500">/month</p>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-4">Usage This Month</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Emails Sent</span>
                  <span className="font-medium">{formatNumber(user.organization_details.emails_sent_this_month)} / {formatNumber(user.organization_details.plan_details?.monthly_email_limit || 0)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-primary-600 h-2 rounded-full transition-all"
                    style={{ width: `${Math.min(100, (user.organization_details.emails_sent_this_month / (user.organization_details.plan_details?.monthly_email_limit || 1)) * 100)}%` }}
                  />
                </div>
              </div>
              <p className="text-sm text-gray-500">
                {formatNumber(user.organization_details.remaining_emails)} emails remaining
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Team */}
      {tab === 'team' && (
        <div className="max-w-2xl">
          <div className="card p-0 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Member</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {members.map((member) => (
                  <tr key={member.id}>
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{member.full_name || member.email}</p>
                      <p className="text-sm text-gray-500">{member.email}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="badge badge-info">{member.role}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
