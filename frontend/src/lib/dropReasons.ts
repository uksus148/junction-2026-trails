import type { DropReason } from '../types'

export const DROP_REASON_LABELS: Record<DropReason, string> = {
  dislike: "you said it's not for you",
  budget: 'over your budget',
  closed: "closed by the time you'd get there",
  no_time: "doesn't fit in your day",
  walk_limit: 'over your walking limit',
  skipped_by_user: 'you skipped it',
}
