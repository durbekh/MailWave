import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { fetchTemplate, createTemplate, updateTemplate, clearCurrentTemplate } from '../store/templateSlice';

export default function TemplateEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { currentTemplate } = useAppSelector((state) => state.templates);
  const isNew = !id || id === 'new';

  const [form, setForm] = useState({
    name: '', description: '', subject: '', preview_text: '', html_content: '',
  });
  const [previewMode, setPreviewMode] = useState(false);

  useEffect(() => {
    if (!isNew && id) dispatch(fetchTemplate(id));
    return () => { dispatch(clearCurrentTemplate()); };
  }, [dispatch, id, isNew]);

  useEffect(() => {
    if (currentTemplate && !isNew) {
      setForm({
        name: currentTemplate.name, description: currentTemplate.description,
        subject: currentTemplate.subject, preview_text: currentTemplate.preview_text,
        html_content: currentTemplate.html_content,
      });
    }
  }, [currentTemplate, isNew]);

  const update = (field: string, value: string) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSave = async () => {
    try {
      if (isNew) {
        const result = await dispatch(createTemplate(form)).unwrap();
        toast.success('Template created');
        navigate(`/templates/${result.id}/edit`);
      } else if (id) {
        await dispatch(updateTemplate({ id, data: form })).unwrap();
        toast.success('Template saved');
      }
    } catch {
      toast.error('Failed to save template');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{isNew ? 'New Template' : 'Edit Template'}</h1>
          {!isNew && currentTemplate && (
            <p className="text-gray-500 mt-1">{currentTemplate.name}</p>
          )}
        </div>
        <div className="flex gap-3">
          <button onClick={() => setPreviewMode(!previewMode)} className="btn-secondary">
            {previewMode ? 'Edit' : 'Preview'}
          </button>
          <button onClick={handleSave} className="btn-primary">Save Template</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings panel */}
        <div className="card space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Template Name</label>
            <input type="text" value={form.name} onChange={(e) => update('name', e.target.value)} className="input-field" placeholder="e.g. Welcome Email" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={form.description} onChange={(e) => update('description', e.target.value)} className="input-field" rows={2} placeholder="Brief description of this template" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Subject</label>
            <input type="text" value={form.subject} onChange={(e) => update('subject', e.target.value)} className="input-field" placeholder="Email subject line" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Preview Text</label>
            <input type="text" value={form.preview_text} onChange={(e) => update('preview_text', e.target.value)} className="input-field" placeholder="Inbox preview text" />
          </div>

          {/* Merge tags helper */}
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Available Merge Tags</h3>
            <div className="flex flex-wrap gap-1">
              {['first_name', 'last_name', 'email', 'company', 'city'].map((tag) => (
                <button key={tag}
                  onClick={() => update('html_content', form.html_content + `{{${tag}}}`)}
                  className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-primary-50 hover:text-primary-600"
                >{`{{${tag}}}`}</button>
              ))}
            </div>
          </div>
        </div>

        {/* Content editor / preview */}
        <div className="lg:col-span-2 card p-0 overflow-hidden">
          {previewMode ? (
            <div className="p-6">
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 text-xs text-gray-500 border-b border-gray-200">
                  Preview
                </div>
                <div className="p-4 bg-white min-h-[400px]"
                  dangerouslySetInnerHTML={{ __html: form.html_content || '<p style="color:#999;">No content yet</p>' }}
                />
              </div>
            </div>
          ) : (
            <div className="p-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">HTML Content</label>
              <textarea
                value={form.html_content}
                onChange={(e) => update('html_content', e.target.value)}
                className="w-full h-[500px] font-mono text-sm p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Paste or write your HTML email template here..."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
