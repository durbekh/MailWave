/* ==============================
   Core domain types for MailWave
   ============================== */

// --- Auth / Users ---
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  organization: string;
  organization_details?: Organization;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  phone: string;
  avatar: string | null;
  timezone: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Plan {
  id: string;
  name: string;
  tier: 'free' | 'starter' | 'professional' | 'enterprise';
  monthly_email_limit: number;
  max_contacts: number;
  max_campaigns_per_month: number;
  max_automation_sequences: number;
  ab_testing_enabled: boolean;
  advanced_analytics: boolean;
  custom_templates: boolean;
  priority_support: boolean;
  price_monthly: string;
  price_yearly: string;
  is_active: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  plan_details?: Plan;
  website: string;
  logo: string | null;
  default_from_email: string;
  default_from_name: string;
  default_reply_to: string;
  emails_sent_this_month: number;
  remaining_emails: number;
  email_limit_reached: boolean;
  member_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

// --- Campaigns ---
export type CampaignStatus = 'draft' | 'scheduled' | 'sending' | 'sent' | 'paused' | 'cancelled' | 'failed';
export type CampaignType = 'regular' | 'ab_test' | 'automated';

export interface Campaign {
  id: string;
  name: string;
  subject: string;
  preview_text: string;
  from_name: string;
  from_email: string;
  reply_to: string;
  html_content: string;
  plain_text_content: string;
  template: string | null;
  status: CampaignStatus;
  campaign_type: CampaignType;
  track_opens: boolean;
  track_clicks: boolean;
  total_recipients: number;
  total_sent: number;
  total_delivered: number;
  total_opens: number;
  unique_opens: number;
  total_clicks: number;
  unique_clicks: number;
  total_bounces: number;
  total_unsubscribes: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  unsubscribe_rate: number;
  sent_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// --- Contacts ---
export type ContactStatus = 'subscribed' | 'unsubscribed' | 'bounced' | 'cleaned' | 'pending';

export interface Contact {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  company: string;
  phone: string;
  city: string;
  state: string;
  country: string;
  status: ContactStatus;
  source: string;
  lead_score: number;
  engagement_rate: number;
  total_emails_received: number;
  total_opens: number;
  total_clicks: number;
  tags_detail: Tag[];
  lists_detail: ContactList[];
  created_at: string;
  updated_at: string;
}

export interface ContactList {
  id: string;
  name: string;
  description: string;
  is_default: boolean;
  double_optin: boolean;
  contact_count: number;
  unsubscribed_count: number;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  name: string;
  color: string;
  created_at: string;
}

export interface Segment {
  id: string;
  name: string;
  description: string;
  match_type: 'all' | 'any';
  rules: SegmentRule[];
  contact_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SegmentRule {
  id: string;
  field: string;
  operator: string;
  value: string;
}

// --- Templates ---
export interface EmailTemplate {
  id: string;
  name: string;
  description: string;
  subject: string;
  preview_text: string;
  html_content: string;
  json_content: Record<string, unknown>;
  template_type: 'system' | 'custom' | 'shared';
  category: string | null;
  category_name: string;
  thumbnail: string | null;
  is_active: boolean;
  is_starred: boolean;
  usage_count: number;
  merge_tags: string[];
  created_at: string;
  updated_at: string;
}

// --- Automation ---
export type AutomationStatus = 'draft' | 'active' | 'paused' | 'archived';

export interface AutomationWorkflow {
  id: string;
  name: string;
  description: string;
  status: AutomationStatus;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  steps: AutomationStep[];
  step_count: number;
  total_enrolled: number;
  total_completed: number;
  total_exited: number;
  currently_active: number;
  conversion_rate: number;
  created_at: string;
  updated_at: string;
}

export interface AutomationStep {
  id: string;
  step_type: string;
  name: string;
  position: number;
  email_template: string | null;
  email_subject: string;
  email_content: string;
  delay_amount: number;
  delay_unit: string;
  condition_config: Record<string, unknown>;
  action_config: Record<string, unknown>;
  is_active: boolean;
  total_entered: number;
  total_completed: number;
}

// --- Analytics ---
export interface DailyStats {
  id: string;
  date: string;
  emails_sent: number;
  emails_delivered: number;
  unique_opens: number;
  unique_clicks: number;
  bounces: number;
  unsubscribes: number;
  new_contacts: number;
  open_rate: number;
  click_rate: number;
}

export interface DashboardSummary {
  total_contacts: number;
  active_contacts: number;
  total_campaigns: number;
  campaigns_sent_this_month: number;
  emails_sent_this_month: number;
  average_open_rate: number;
  average_click_rate: number;
  active_automations: number;
  contacts_added_this_month: number;
  unsubscribes_this_month: number;
}

// --- Pagination ---
export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
