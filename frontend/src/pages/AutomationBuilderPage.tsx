import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchWorkflow, createWorkflow, updateWorkflow, clearCurrentWorkflow } from '../store/automationSlice';
import type { AutomationStep } from '../types';

const STEP_TYPES = [
  { value: 'send_email', label: 'Send Email', icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8' },
  { value: 'wait_delay', label: 'Wait / Delay', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  { value: 'condition', label: 'If/Else', icon: 'M8 9l4-4 4 4m0 6l-4 4-4-4' },
  { value: 'add_tag', label: 'Add Tag', icon: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z' },
  { value: 'add_to_list', label: 'Add to List', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { value: 'webhook', label: 'Webhook', icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' },
  { value: 'notify_team', label: 'Notify Team', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
];

const TRIGGER_TYPES = [
  { value: 'subscription', label: 'Subscriber Joins List' },
  { value: 'tag_added', label: 'Tag Added' },
  { value: 'form_submit', label: 'Form Submitted' },
  { value: 'manual', label: 'Manual Enrollment' },
  { value: 'campaign_activity', label: 'Campaign Activity' },
  { value: 'api_event', label: 'API Event' },
];

export default function AutomationBuilderPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { currentWorkflow } = useAppSelector((state) => state.automation);
  const isNew = !id;

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [triggerType, setTriggerType] = useState('subscription');
  const [steps, setSteps] = useState<Partial<AutomationStep>[]>([]);

  useEffect(() => {
    if (id) dispatch(fetchWorkflow(id));
    return () => { dispatch(clearCurrentWorkflow()); };
  }, [dispatch, id]);

  useEffect(() => {
    if (currentWorkflow && id) {
      setName(currentWorkflow.name);
      setDescription(currentWorkflow.description);
      setTriggerType(currentWorkflow.trigger_type);
      setSteps(currentWorkflow.steps || []);
    }
  }, [currentWorkflow, id]);

  const addStep = (stepType: string) => {
    const label = STEP_TYPES.find((s) => s.value === stepType)?.label || stepType;
    setSteps((prev) => [
      ...prev,
      {
        step_type: stepType,
        name: label,
        position: prev.length,
        email_subject: '',
        email_content: '',
        delay_amount: stepType === 'wait_delay' ? 1 : 0,
        delay_unit: 'days',
        condition_config: {},
        action_config: {},
        is_active: true,
      },
    ]);
  };

  const removeStep = (index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const updateStep = (index: number, field: string, value: unknown) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)));
  };

  const handleSave = async () => {
    const data = {
      name, description, trigger_type: triggerType, trigger_config: {},
      steps: steps.map((s, i) => ({ ...s, position: i })),
    };
    try {
      if (isNew) {
        const result = await dispatch(createWorkflow(data)).unwrap();
        toast.success('Automation created');
        navigate(`/automation/${result.id}/edit`);
      } else if (id) {
        await dispatch(updateWorkflow({ id, data })).unwrap();
        toast.success('Automation saved');
      }
    } catch {
      toast.error('Failed to save automation');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{isNew ? 'New Automation' : 'Edit Automation'}</h1>
        <button onClick={handleSave} className="btn-primary">Save Automation</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Config panel */}
        <div className="card space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Automation Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field" placeholder="e.g. Welcome Sequence" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="input-field" rows={2} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Trigger</label>
            <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)} className="input-field">
              {TRIGGER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>

          <hr className="my-4" />
          <h3 className="text-sm font-medium text-gray-700">Add Step</h3>
          <div className="grid grid-cols-2 gap-2">
            {STEP_TYPES.map((st) => (
              <button key={st.value} onClick={() => addStep(st.value)}
                className="flex items-center gap-2 p-2 text-xs text-gray-600 bg-gray-50 rounded-lg hover:bg-primary-50 hover:text-primary-600 transition-colors"
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={st.icon} />
                </svg>
                {st.label}
              </button>
            ))}
          </div>
        </div>

        {/* Workflow canvas */}
        <div className="lg:col-span-2">
          {/* Trigger node */}
          <div className="card mb-2 border-l-4 border-l-green-500">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Trigger</p>
                <p className="text-xs text-gray-500">{TRIGGER_TYPES.find((t) => t.value === triggerType)?.label}</p>
              </div>
            </div>
          </div>

          {/* Connector */}
          {steps.length > 0 && <div className="w-px h-6 bg-gray-300 mx-auto" />}

          {/* Steps */}
          {steps.map((step, index) => (
            <div key={index}>
              <div className="card mb-2 border-l-4 border-l-primary-400">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded font-medium">
                        {STEP_TYPES.find((s) => s.value === step.step_type)?.label || step.step_type}
                      </span>
                      <span className="text-xs text-gray-400">Step {index + 1}</span>
                    </div>

                    {step.step_type === 'send_email' && (
                      <div className="space-y-2">
                        <input type="text" value={step.email_subject || ''} onChange={(e) => updateStep(index, 'email_subject', e.target.value)}
                          className="input-field text-sm" placeholder="Email subject" />
                        <textarea value={step.email_content || ''} onChange={(e) => updateStep(index, 'email_content', e.target.value)}
                          className="input-field text-sm" rows={3} placeholder="Email HTML content" />
                      </div>
                    )}

                    {step.step_type === 'wait_delay' && (
                      <div className="flex gap-2 items-center">
                        <span className="text-sm text-gray-500">Wait for</span>
                        <input type="number" value={step.delay_amount || 1} onChange={(e) => updateStep(index, 'delay_amount', Number(e.target.value))}
                          className="input-field w-20 text-sm" min={1} />
                        <select value={step.delay_unit || 'days'} onChange={(e) => updateStep(index, 'delay_unit', e.target.value)} className="input-field w-28 text-sm">
                          <option value="minutes">Minutes</option>
                          <option value="hours">Hours</option>
                          <option value="days">Days</option>
                          <option value="weeks">Weeks</option>
                        </select>
                      </div>
                    )}

                    {step.step_type === 'condition' && (
                      <input type="text" value={step.name || ''} onChange={(e) => updateStep(index, 'name', e.target.value)}
                        className="input-field text-sm" placeholder="Condition description (e.g. Has opened email)" />
                    )}

                    {(step.step_type === 'add_tag' || step.step_type === 'add_to_list') && (
                      <input type="text" value={step.name || ''} onChange={(e) => updateStep(index, 'name', e.target.value)}
                        className="input-field text-sm" placeholder="Step label" />
                    )}
                  </div>
                  <button onClick={() => removeStep(index)} className="text-gray-400 hover:text-red-500 p-1 ml-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              {index < steps.length - 1 && <div className="w-px h-6 bg-gray-300 mx-auto" />}
            </div>
          ))}

          {steps.length === 0 && (
            <div className="card text-center py-12 border-dashed">
              <p className="text-gray-400">No steps yet. Add steps from the panel on the left.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
