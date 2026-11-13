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
  /план\s+(?:на\s+)?д(?:ень|ня)/iu,
  /распис/iu,
  /на\s+весь\s+день/iu,
]

export function detectDayPlan(text: string): boolean {
  return DAY_PLAN_PATTERNS.some((pattern) => pattern.test(text))
}

const TOPICS: { tag: string; words: string }[] = [
  { tag: 'museum', words: 'museums?|galler(?:y|ies)|музе\\p{L}*|галере\\p{L}*' },
  { tag: 'castle', words: 'castles?|fortress(?:es)?|замок|замк\\p{L}*|крепост\\p{L}*' },
  { tag: 'church', words: 'church(?:es)?|cathedrals?|церк\\p{L}*|собор\\p{L}*|храм\\p{L}*' },
  { tag: 'viewpoint', words: 'views?|viewpoints?|lookouts?|panoram\\p{L}*|вид(?:ы|ов|ами)?|смотров\\p{L}*' },
  { tag: 'nature', words: 'nature|parks?|forests?|природ\\p{L}*|парк\\p{L}*|лес(?:а|ов)?' },
  { tag: 'waterfall', words: 'waterfalls?|водопад\\p{L}*' },
  { tag: 'lake', words: 'lakes?|озер\\p{L}*|озёр\\p{L}*' },
  { tag: 'peak', words: 'peaks?|summits?|mountains?|вершин\\p{L}*|гор(?:ы|у|ам)' },
]

// Short negations only count right before the topic ("no museums"); bare "not" is too loose ("do not miss the castle").
const NEGATIVE_ADJACENT = 'no|without|без'
const NEGATIVE = "skip|avoid|hate|dislike|don'?t\\s+(?:like|want|care\\s+for)|do\\s+not\\s+(?:like|want)|not\\s+into|не\\s+люблю|не\\s+хочу|не\\s+нравятся|ненавижу"
const POSITIVE = 'love|like|into|enjoy|want\\s+to\\s+see|interested\\s+in|люблю|нравятся|нравится|обожаю|хочу\\s+увидеть|интересуют'
const UP_TO_TWO_WORDS = "(?:[\\s,]+[\\p{L}'-]+){0,2}?[\\s,]+"
const ADJACENT = '\\s+'

const mentionAfter = (trigger: string, words: string, gap = UP_TO_TWO_WORDS) =>
  new RegExp(`(?<!\\p{L})(?:${trigger})${gap}(?:${words})(?!\\p{L})`, 'iu')

const isDisliked = (words: string, text: string) =>
  mentionAfter(NEGATIVE, words).test(text) || mentionAfter(NEGATIVE_ADJACENT, words, ADJACENT).test(text)

const CROWDS = /crowd|tourist\s+trap|толп|людн/iu
const RELAXED = /\bslow\b|relax|chill|no\s+rush|спокойн|не\s+спеша|медленн|неторопл/iu
const INTENSE = /\bfast\b|intense|packed|as\s+much\s+as\s+possible|максимум|быстр|интенсивн/iu
const FREE = /\bfree\b|no\s+money|бесплатн/iu
const CHEAP = /cheap|budget|low[\s-]cost|inexpensive|дешев|дёшев|недорог|эконом/iu
const DISTANCE = /(\d+(?:[.,]\d+)?)\s*(?:km|км)/iu

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

const START_TIME = /(?<!\p{L})(?:from|starting(?:\s+at)?|с|от)\s+(\d{1,2})(?:[:.](\d{2}))?(?!\d)(\s*(?:am|pm|h|o'?clock|час|утра))?/iu
const END_TIME = /(?<!\p{L})(?:until|till|to|до)\s+(\d{1,2})(?:[:.](\d{2}))?(?!\d)/iu
const LAST_HOUR = 23
const NOON_HOUR = 12

type ClockMatch = { minutes: number; explicit: boolean }

function clockFrom(pattern: RegExp, text: string): ClockMatch | undefined {
  const match = pattern.exec(text)
  if (!match || Number(match[1]) > LAST_HOUR) return undefined
  return { minutes: Number(match[1]) * 60 + Number(match[2] ?? 0), explicit: match[2] !== undefined || Boolean(match[3]) }
}

/**
 * "from 10 to 6" means until 18:00. A bare number after "с/from" only counts as a time
 * when it looks like one (has minutes, a unit, or an end time follows) — "с 2 детьми" is not 02:00.
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
