import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';

/**
 * Format a date string into a human-readable date.
 */
export function formatDate(dateStr: string | null | undefined, pattern = 'MMM d, yyyy'): string {
  if (!dateStr) return '--';
  const date = parseISO(dateStr);
  if (!isValid(date)) return '--';
  return format(date, pattern);
}

/**
 * Format a date string into a date with time.
 */
export function formatDateTime(dateStr: string | null | undefined): string {
  return formatDate(dateStr, 'MMM d, yyyy h:mm a');
}

/**
 * Format a date as relative time (e.g., "3 hours ago").
 */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '--';
  const date = parseISO(dateStr);
  if (!isValid(date)) return '--';
  return formatDistanceToNow(date, { addSuffix: true });
}

/**
 * Format a number with commas (e.g., 1,234,567).
 */
export function formatNumber(num: number | undefined | null): string {
  if (num === undefined || num === null) return '0';
  return num.toLocaleString();
}

/**
 * Format a percentage value.
 */
export function formatPercent(value: number | undefined | null, decimals = 1): string {
  if (value === undefined || value === null) return '0%';
  return `${value.toFixed(decimals)}%`;
}

/**
 * Truncate a string to a maximum length.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + '...';
}

/**
 * Get a color class for a campaign status badge.
 */
export function getStatusColor(campaignStatus: string): string {
  const colors: Record<string, string> = {
    draft: 'badge-gray',
    scheduled: 'badge-info',
    sending: 'badge-warning',
    sent: 'badge-success',
    paused: 'badge-warning',
    cancelled: 'badge-danger',
    failed: 'badge-danger',
    active: 'badge-success',
    archived: 'badge-gray',
    subscribed: 'badge-success',
    unsubscribed: 'badge-danger',
    bounced: 'badge-danger',
    cleaned: 'badge-gray',
    pending: 'badge-warning',
  };
  return colors[campaignStatus] || 'badge-gray';
}

/**
 * Generate initials from a name.
 */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}
