import { describe, expect, it } from 'vitest'
import { detectDayPlan, extractPreferencesPatch, extractTimeWindow } from './intent'

describe('detectDayPlan', () => {
  it.each(['Plan my day in Bratislava', 'Make me an itinerary for tomorrow', 'Составь план на день в Братиславе', 'нужно расписание на завтра'])(
    'recognises "%s"',
    (text) => expect(detectDayPlan(text)).toBe(true),
  )

  it('ignores ordinary route requests', () => {
    expect(detectDayPlan('Hike from Štrbské Pleso to Rysy past a waterfall')).toBe(false)
  })
})

describe('extractPreferencesPatch', () => {
  it('reads dislikes, crowds, pace, budget and walking distance', () => {
    expect(extractPreferencesPatch('No museums please, I hate crowds, slow pace, cheap, max 5 km of walking')).toEqual({
      dislikes: ['museum'],
      avoidCrowds: true,
      pace: 'relaxed',
      budget: 1,
      maxWalkKm: 5,
    })
  })

  it('reads Russian phrasing and interests', () => {
    expect(extractPreferencesPatch('Люблю замки, без музеев, не спеша')).toEqual({
      interests: ['castle'],
      dislikes: ['museum'],
      pace: 'relaxed',
    })
  })

  it('does not treat "don\'t like" as an interest', () => {
    expect(extractPreferencesPatch("I don't like churches")).toEqual({ dislikes: ['church'] })
  })

  it('returns an empty patch when nothing is mentioned', () => {
    expect(extractPreferencesPatch('Bratislava tomorrow')).toEqual({})
  })
})

describe('extractTimeWindow', () => {
  it('reads start and end times', () => {
    expect(extractTimeWindow('plan my day from 9:30 until 17')).toEqual({ startTime: '09:30', endTime: '17:00' })
    expect(extractTimeWindow('план на день с 11 до 19:00')).toEqual({ startTime: '11:00', endTime: '19:00' })
  })
})
