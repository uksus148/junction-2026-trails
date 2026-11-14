// Lightweight intent parsing for mock mode (EN/RU). The real agent does this with an LLM and returns the same shapes.
import type { Budget, Preferences } from '../types'
import { fromMinutes } from './time'

const DAY_PLAN_PATTERNS = [
  /\bplan\s+(?:my|the|a|our)\s+(?:whole\s+)?day\b/i,
  /\bday\s+plan\b/i,
  /\bitinerar/i,
  /\bschedule\s+for\s+(?:my|the|a|our)\s+(?:whole\s+)?day\b/i,
  /\bday\s+schedule\b/i,
  /\bfull\s+day\b/i,
  /\u043f\u043b\u0430\u043d\s+(?:\u043d\u0430\s+)?\u0434(?:\u0435\u043d\u044c|\u043d\u044f)/iu,
  /\u0440\u0430\u0441\u043f\u0438\u0441/iu,
  /\u043d\u0430\s+\u0432\u0435\u0441\u044c\s+\u0434\u0435\u043d\u044c/iu,
]

export function detectDayPlan(text: string): boolean {
  return DAY_PLAN_PATTERNS.some((pattern) => pattern.test(text))
}

const TOPICS: { tag: string; words: string }[] = [
  { tag: 'museum', words: 'museums?|galler(?:y|ies)|\u043c\u0443\u0437\u0435\\p{L}*|\u0433\u0430\u043b\u0435\u0440\u0435\\p{L}*' },
  { tag: 'castle', words: 'castles?|fortress(?:es)?|\u0437\u0430\u043c\u043e\u043a|\u0437\u0430\u043c\u043a\\p{L}*|\u043a\u0440\u0435\u043f\u043e\u0441\u0442\\p{L}*' },
  { tag: 'church', words: 'church(?:es)?|cathedrals?|\u0446\u0435\u0440\u043a\\p{L}*|\u0441\u043e\u0431\u043e\u0440\\p{L}*|\u0445\u0440\u0430\u043c\\p{L}*' },
  { tag: 'viewpoint', words: 'views?|viewpoints?|lookouts?|panoram\\p{L}*|\u0432\u0438\u0434(?:\u044b|\u043e\u0432|\u0430\u043c\u0438)?|\u0441\u043c\u043e\u0442\u0440\u043e\u0432\\p{L}*' },
  { tag: 'nature', words: 'nature|parks?|forests?|\u043f\u0440\u0438\u0440\u043e\u0434\\p{L}*|\u043f\u0430\u0440\u043a\\p{L}*|\u043b\u0435\u0441(?:\u0430|\u043e\u0432)?' },
  { tag: 'waterfall', words: 'waterfalls?|\u0432\u043e\u0434\u043e\u043f\u0430\u0434\\p{L}*' },
  { tag: 'lake', words: 'lakes?|\u043e\u0437\u0435\u0440\\p{L}*|\u043e\u0437\u0451\u0440\\p{L}*' },
  { tag: 'peak', words: 'peaks?|summits?|mountains?|\u0432\u0435\u0440\u0448\u0438\u043d\\p{L}*|\u0433\u043e\u0440(?:\u044b|\u0443|\u0430\u043c)' },
]

// Short negations only count right before the topic ("no museums"); bare "not" is too loose ("do not miss the castle").
const NEGATIVE_ADJACENT = 'no|without|\u0431\u0435\u0437'
const NEGATIVE = "skip|avoid|hate|dislike|don'?t\\s+(?:like|want|care\\s+for)|do\\s+not\\s+(?:like|want)|not\\s+into|\u043d\u0435\\s+\u043b\u044e\u0431\u043b\u044e|\u043d\u0435\\s+\u0445\u043e\u0447\u0443|\u043d\u0435\\s+\u043d\u0440\u0430\u0432\u044f\u0442\u0441\u044f|\u043d\u0435\u043d\u0430\u0432\u0438\u0436\u0443"
const POSITIVE = 'love|like|into|enjoy|want\\s+to\\s+see|interested\\s+in|\u043b\u044e\u0431\u043b\u044e|\u043d\u0440\u0430\u0432\u044f\u0442\u0441\u044f|\u043d\u0440\u0430\u0432\u0438\u0442\u0441\u044f|\u043e\u0431\u043e\u0436\u0430\u044e|\u0445\u043e\u0447\u0443\\s+\u0443\u0432\u0438\u0434\u0435\u0442\u044c|\u0438\u043d\u0442\u0435\u0440\u0435\u0441\u0443\u044e\u0442'
const UP_TO_TWO_WORDS = "(?:[\\s,]+[\\p{L}'-]+){0,2}?[\\s,]+"
const ADJACENT = '\\s+'

const mentionAfter = (trigger: string, words: string, gap = UP_TO_TWO_WORDS) =>
  new RegExp(`(?<!\\p{L})(?:${trigger})${gap}(?:${words})(?!\\p{L})`, 'iu')

const isDisliked = (words: string, text: string) =>
  mentionAfter(NEGATIVE, words).test(text) || mentionAfter(NEGATIVE_ADJACENT, words, ADJACENT).test(text)

const CROWDS = /crowd|tourist\s+trap|\u0442\u043e\u043b\u043f|\u043b\u044e\u0434\u043d/iu
const RELAXED = /\bslow\b|relax|chill|no\s+rush|\u0441\u043f\u043e\u043a\u043e\u0439\u043d|\u043d\u0435\s+\u0441\u043f\u0435\u0448\u0430|\u043c\u0435\u0434\u043b\u0435\u043d\u043d|\u043d\u0435\u0442\u043e\u0440\u043e\u043f\u043b/iu
const INTENSE = /\bfast\b|intense|packed|as\s+much\s+as\s+possible|\u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c|\u0431\u044b\u0441\u0442\u0440|\u0438\u043d\u0442\u0435\u043d\u0441\u0438\u0432\u043d/iu
const FREE = /\bfree\b|no\s+money|\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d/iu
const CHEAP = /cheap|budget|low[\s-]cost|inexpensive|\u0434\u0435\u0448\u0435\u0432|\u0434\u0451\u0448\u0435\u0432|\u043d\u0435\u0434\u043e\u0440\u043e\u0433|\u044d\u043a\u043e\u043d\u043e\u043c/iu
const DISTANCE = /(\d+(?:[.,]\d+)?)\s*(?:km|\u043a\u043c)/iu

function budgetFrom(text: string): Budget | undefined {
  if (FREE.test(text)) return 0
  if (CHEAP.test(text)) return 1
  return undefined
}

/** Pull preferences out of free text. Only keys that were actually mentioned are returned. */
export function extractPreferencesPatch(text: string): Partial<Preferences> {
  const dislikes = TOPICS.filter((t) => isDisliked(t.words, text)).map((t) => t.tag)
  const interests = TOPICS.filter((t) => !dislikes.includes(t.tag) && mentionAfter(POSITIVE, t.words).test(text)).map((t) => t.tag)
  const pace = RELAXED.test(text) ? 'relaxed' : INTENSE.test(text) ? 'intense' : undefined
  const budget = budgetFrom(text)
  const distance = DISTANCE.exec(text)
  return {
    ...(interests.length > 0 && { interests }),
    ...(dislikes.length > 0 && { dislikes }),
    ...(CROWDS.test(text) && { avoidCrowds: true }),
    ...(pace && { pace }),
    ...(budget !== undefined && { budget }),
    ...(distance && { maxWalkKm: Number(distance[1].replace(',', '.')) }),
  }
}

const START_TIME = /(?<!\p{L})(?:from|starting(?:\s+at)?|\u0441|\u043e\u0442)\s+(\d{1,2})(?:[:.](\d{2}))?(?!\d)(\s*(?:am|pm|h|o'?clock|\u0447\u0430\u0441|\u0443\u0442\u0440\u0430))?/iu
const END_TIME = /(?<!\p{L})(?:until|till|to|\u0434\u043e)\s+(\d{1,2})(?:[:.](\d{2}))?(?!\d)/iu
const LAST_HOUR = 23
const NOON_HOUR = 12

type ClockMatch = { minutes: number; explicit: boolean }

function clockFrom(pattern: RegExp, text: string): ClockMatch | undefined {
  const match = pattern.exec(text)
  if (!match || Number(match[1]) > LAST_HOUR) return undefined
  return { minutes: Number(match[1]) * 60 + Number(match[2] ?? 0), explicit: match[2] !== undefined || Boolean(match[3]) }
}

/**
 * "from 10 to 6" means until 18:00. A bare number after "\u0441/from" only counts as a time
 * when it looks like one (has minutes, a unit, or an end time follows) — "\u0441 2 \u0434\u0435\u0442\u044c\u043c\u0438" is not 02:00.
 */
export function extractTimeWindow(text: string): { startTime?: string; endTime?: string } {
  const end = clockFrom(END_TIME, text)
  const start = clockFrom(START_TIME, text)
  const startMin = start && (start.explicit || end) ? start.minutes : undefined
  const afternoon = (min: number) => (startMin !== undefined && min <= startMin && min < NOON_HOUR * 60 ? min + NOON_HOUR * 60 : min)
  const endMin = end && afternoon(end.minutes)
  const validEnd = endMin !== undefined && (startMin === undefined || endMin > startMin) ? endMin : undefined
  return {
    ...(startMin !== undefined && { startTime: fromMinutes(startMin) }),
    ...(validEnd !== undefined && { endTime: fromMinutes(validEnd) }),
  }
}
