import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchCampaign, createCampaign, updateCampaign, sendCampaign, clearCurrentCampaign } from '../store/campaignSlice';
import { fetchLists, fetchSegments } from '../store/contactSlice';

type BuilderStep = 'setup' | 'content' | 'recipients' | 'review';

export default function CampaignBuilderPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { currentCampaign } = useAppSelector((state) => state.campaigns);
  const { lists, segments } = useAppSelector((state) => state.contacts);
  const [step, setStep] = useState<BuilderStep>('setup');
  const [form, setForm] = useState({
    name: '', subject: '', preview_text: '', from_name: '',
    from_email: '', reply_to: '', html_content: '',
    campaign_type: 'regular' as const, track_opens: true, track_clicks: true,
    contact_list_ids: [] as string[], segment_ids: [] as string[],
  });
  const [testEmail, setTestEmail] = useState('');

  useEffect(() => {
    dispatch(fetchLists());
    dispatch(fetchSegments());
    if (id) {
      dispatch(fetchCampaign(id));
    }
    return () => { dispatch(clearCurrentCampaign()); };
  }, [dispatch, id]);

  useEffect(() => {
    if (currentCampaign && id) {
      setForm({
        name: currentCampaign.name, subject: currentCampaign.subject,
        preview_text: currentCampaign.preview_text, from_name: currentCampaign.from_name,
        from_email: currentCampaign.from_email, reply_to: currentCampaign.reply_to,
        html_content: currentCampaign.html_content, campaign_type: currentCampaign.campaign_type,
        track_opens: currentCampaign.track_opens, track_clicks: currentCampaign.track_clicks,
        contact_list_ids: [], segment_ids: [],
      });
    }
  }, [currentCampaign, id]);

  const update = (field: string, value: unknown) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSave = async () => {
    try {
      if (id) {
        await dispatch(updateCampaign({ id, data: form })).unwrap();
        toast.success('Campaign saved');
      } else {
        const result = await dispatch(createCampaign(form)).unwrap();
        toast.success('Campaign created');
        navigate(`/campaigns/${result.id}/edit`);
      }
    } catch {
      toast.error('Failed to save campaign');
    }
  };

  const handleSend = async () => {
    if (!id) return;
    if (!window.confirm('Send this campaign now?')) return;
    try {
      await dispatch(sendCampaign({ id, data: { send_immediately: true } })).unwrap();
      toast.success('Campaign queued for sending');
      navigate('/campaigns');
    } catch {
      toast.error('Failed to send campaign');
    }
  };

  const handleSendTest = async () => {
    if (!id || !testEmail) return;
    try {
      await dispatch(sendCampaign({ id, data: { test_email: testEmail } })).unwrap();
      toast.success(`Test email sent to ${testEmail}`);
    } catch {
      toast.error('Failed to send test');
    }
  };

  const steps: { key: BuilderStep; label: string }[] = [
    { key: 'setup', label: 'Setup' },
    { key: 'content', label: 'Content' },
    { key: 'recipients', label: 'Recipients' },
    { key: 'review', label: 'Review & Send' },
  ];

  const toggleList = (listId: string) => {
    setForm((prev) => ({
      ...prev,
      contact_list_ids: prev.contact_list_ids.includes(listId)
        ? prev.contact_list_ids.filter((l) => l !== listId)
        : [...prev.contact_list_ids, listId],
    }));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{id ? 'Edit Campaign' : 'New Campaign'}</h1>
        <div className="flex gap-3">
          <button onClick={handleSave} className="btn-secondary">Save Draft</button>
          {id && <button onClick={handleSend} className="btn-primary">Send Campaign</button>}
        </div>
      </div>

      {/* Step Nav */}
      <div className="flex gap-1 mb-8 bg-gray-100 rounded-lg p-1">
        {steps.map((s) => (
          <button key={s.key} onClick={() => setStep(s.key)}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${step === s.key ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >{s.label}</button>
        ))}
      </div>

      {/* Step Content */}
      <div className="card">
        {step === 'setup' && (
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name</label>
              <input type="text" value={form.name} onChange={(e) => update('name', e.target.value)} className="input-field" placeholder="e.g. Spring Sale Announcement" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Subject Line</label>
              <input type="text" value={form.subject} onChange={(e) => update('subject', e.target.value)} className="input-field" placeholder="e.g. Don't miss our spring sale!" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preview Text</label>
              <input type="text" value={form.preview_text} onChange={(e) => update('preview_text', e.target.value)} className="input-field" placeholder="Brief preview shown in inbox" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">From Name</label>
                <input type="text" value={form.from_name} onChange={(e) => update('from_name', e.target.value)} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">From Email</label>
                <input type="email" value={form.from_email} onChange={(e) => update('from_email', e.target.value)} className="input-field" />
              </div>
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.track_opens} onChange={(e) => update('track_opens', e.target.checked)} className="rounded" /> Track opens
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.track_clicks} onChange={(e) => update('track_clicks', e.target.checked)} className="rounded" /> Track clicks
              </label>
            </div>
          </div>
        )}

        {step === 'content' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email HTML Content</label>
            <textarea value={form.html_content} onChange={(e) => update('html_content', e.target.value)}
              className="input-field font-mono text-sm" rows={20}
              placeholder="<h1>Hello {{first_name}}</h1><p>Your email content here...</p>"
            />
            <p className="text-xs text-gray-400 mt-2">
              Use {'{{first_name}}'}, {'{{last_name}}'}, {'{{email}}'}, {'{{company}}'} as merge tags.
            </p>
          </div>
        )}

        {step === 'recipients' && (
          <div>
            <h3 className="font-medium text-gray-900 mb-4">Select Contact Lists</h3>
            {lists.length === 0 ? (
              <p className="text-gray-500 text-sm">No lists found. Create a list in the Subscribers section first.</p>
            ) : (
              <div className="space-y-2">
                {lists.map((list) => (
                  <label key={list.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                    <input type="checkbox" checked={form.contact_list_ids.includes(list.id)} onChange={() => toggleList(list.id)} className="rounded" />
                    <div className="flex-1">
                      <span className="font-medium text-gray-900">{list.name}</span>
                      <span className="ml-2 text-sm text-gray-500">{list.contact_count} contacts</span>
                    </div>
                  </label>
                ))}
              </div>
            )}

            {segments.length > 0 && (
              <>
                <h3 className="font-medium text-gray-900 mt-6 mb-4">Or Select Segments</h3>
                <div className="space-y-2">
                  {segments.map((seg) => (
                    <label key={seg.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={form.segment_ids.includes(seg.id)} onChange={() =>
                        setForm((prev) => ({
                          ...prev,
                          segment_ids: prev.segment_ids.includes(seg.id)
                            ? prev.segment_ids.filter((s) => s !== seg.id)
                            : [...prev.segment_ids, seg.id],
                        })
                      } className="rounded" />
                      <div className="flex-1">
                        <span className="font-medium text-gray-900">{seg.name}</span>
                        <span className="ml-2 text-sm text-gray-500">~{seg.contact_count} contacts</span>
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {step === 'review' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div><p className="text-sm text-gray-500">Campaign Name</p><p className="font-medium">{form.name || '--'}</p></div>
              <div><p className="text-sm text-gray-500">Subject</p><p className="font-medium">{form.subject || '--'}</p></div>
              <div><p className="text-sm text-gray-500">From</p><p className="font-medium">{form.from_name} &lt;{form.from_email}&gt;</p></div>
              <div><p className="text-sm text-gray-500">Recipients</p><p className="font-medium">{form.contact_list_ids.length} lists, {form.segment_ids.length} segments</p></div>
            </div>
            <hr />
            {id && (
              <div>
                <h3 className="font-medium text-gray-900 mb-2">Send Test Email</h3>
                <div className="flex gap-2">
                  <input type="email" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} className="input-field max-w-xs" placeholder="test@example.com" />
                  <button onClick={handleSendTest} className="btn-secondary">Send Test</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Step Navigation */}
      <div className="flex justify-between mt-6">
        <button onClick={() => { const idx = steps.findIndex((s) => s.key === step); if (idx > 0) setStep(steps[idx - 1].key); }}
          disabled={step === 'setup'} className="btn-secondary"
        >Previous</button>
        <button onClick={() => { const idx = steps.findIndex((s) => s.key === step); if (idx < steps.length - 1) setStep(steps[idx + 1].key); }}
          disabled={step === 'review'} className="btn-primary"
        >Next</button>
      </div>
    </div>
  );
}
