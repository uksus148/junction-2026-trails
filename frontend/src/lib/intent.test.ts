import { describe, expect, it } from 'vitest'
import { detectDayPlan, extractPreferencesPatch, extractTimeWindow } from './intent'

describe('detectDayPlan', () => {
  it.each(['Plan my day in Bratislava', 'Make me an itinerary for tomorrow', '\u0421\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d \u043d\u0430 \u0434\u0435\u043d\u044c \u0432 \u0411\u0440\u0430\u0442\u0438\u0441\u043b\u0430\u0432\u0435', '\u043d\u0443\u0436\u043d\u043e \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430'])(
    'recognises "%s"',
    (text) => expect(detectDayPlan(text)).toBe(true),
  )

  it('ignores ordinary route requests', () => {
    expect(detectDayPlan('Hike from Štrbské Pleso to Rysy past a waterfall')).toBe(false)
  })

  it('does not treat a bus schedule as a day plan', () => {
    expect(detectDayPlan('Hike to Rysy, check the bus schedule back')).toBe(false)
    expect(detectDayPlan('Make a schedule for my day in Bratislava')).toBe(true)
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
    expect(extractPreferencesPatch('\u041b\u044e\u0431\u043b\u044e \u0437\u0430\u043c\u043a\u0438, \u0431\u0435\u0437 \u043c\u0443\u0437\u0435\u0435\u0432, \u043d\u0435 \u0441\u043f\u0435\u0448\u0430')).toEqual({
      interests: ['castle'],
      dislikes: ['museum'],
      pace: 'relaxed',
    })
  })

  it('does not treat "don\'t like" as an interest', () => {
    expect(extractPreferencesPatch("I don't like churches")).toEqual({ dislikes: ['church'] })
  })

  it('does not read "do not miss" as a dislike', () => {
    expect(extractPreferencesPatch('Plan my day, do not miss the castle')).toEqual({})
    expect(extractPreferencesPatch('I do not like museums')).toEqual({ dislikes: ['museum'] })
  })

  it('returns an empty patch when nothing is mentioned', () => {
    expect(extractPreferencesPatch('Bratislava tomorrow')).toEqual({})
  })
})

describe('extractTimeWindow', () => {
  it('reads start and end times', () => {
    expect(extractTimeWindow('plan my day from 9:30 until 17')).toEqual({ startTime: '09:30', endTime: '17:00' })
    expect(extractTimeWindow('\u043f\u043b\u0430\u043d \u043d\u0430 \u0434\u0435\u043d\u044c \u0441 11 \u0434\u043e 19:00')).toEqual({ startTime: '11:00', endTime: '19:00' })
  })

  it('reads "from 10 to 6" as an afternoon end', () => {
    expect(extractTimeWindow('plan my day from 10 to 6')).toEqual({ startTime: '10:00', endTime: '18:00' })
  })

  it('drops an end time that is still before the start', () => {
    expect(extractTimeWindow('from 14:00 until 13:00')).toEqual({ startTime: '14:00' })
  })

  it('does not take a count of people for a start time', () => {
    expect(extractTimeWindow('\u043f\u043b\u0430\u043d \u043d\u0430 \u0434\u0435\u043d\u044c \u0432 \u0411\u0440\u0430\u0442\u0438\u0441\u043b\u0430\u0432\u0435 \u0441 2 \u0434\u0435\u0442\u044c\u043c\u0438')).toEqual({})
  })
})
