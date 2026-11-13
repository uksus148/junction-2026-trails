// Lightweight intent parsing for mock mode (EN/RU). The real agent does this with an LLM and returns the same shapes.
import type { Budget, Preferences } from '../types'

const DAY_PLAN_PATTERNS = [
  /\bplan\s+(?:my|the|a|our)\s+(?:whole\s+)?day\b/i,
  /\bday\s+plan\b/i,
  /\bitinerar/i,
  /\bschedule\b/i,
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

const NEGATIVE = "no|not|without|skip|avoid|hate|dislike|don'?t\\s+(?:like|want|care\\s+for)|not\\s+into|без|не\\s+люблю|не\\s+хочу|не\\s+нравятся|ненавижу"
const POSITIVE = 'love|like|into|enjoy|want\\s+to\\s+see|interested\\s+in|люблю|нравятся|нравится|обожаю|хочу\\s+увидеть|интересуют'
const UP_TO_TWO_WORDS = "(?:[\\s,]+[\\p{L}'-]+){0,2}?[\\s,]+"

const mentionAfter = (trigger: string, words: string) =>
  new RegExp(`(?<!\\p{L})(?:${trigger})${UP_TO_TWO_WORDS}(?:${words})(?!\\p{L})`, 'iu')

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
  const dislikes = TOPICS.filter((t) => mentionAfter(NEGATIVE, t.words).test(text)).map((t) => t.tag)
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

const START_TIME = /(?<!\p{L})(?:from|starting(?:\s+at)?|с|от)\s+(\d{1,2})(?:[:.](\d{2}))?(?!\d)/iu
const END_TIME = /(?<!\p{L})(?:until|till|to|до)\s+(\d{1,2})(?:[:.](\d{2}))?(?!\d)/iu
const LAST_HOUR = 23

function timeFrom(pattern: RegExp, text: string): string | undefined {
  const match = pattern.exec(text)
  if (!match || Number(match[1]) > LAST_HOUR) return undefined
  return `${match[1].padStart(2, '0')}:${match[2] ?? '00'}`
}

export function extractTimeWindow(text: string): { startTime?: string; endTime?: string } {
  const startTime = timeFrom(START_TIME, text)
  const endTime = timeFrom(END_TIME, text)
  return { ...(startTime && { startTime }), ...(endTime && { endTime }) }
}
