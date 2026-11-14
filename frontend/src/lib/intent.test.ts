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
    expect(extractPreferencesPatch('Люблю замки, без музеев, не спеша')).toEqual({
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
    expect(extractTimeWindow('план на день с 11 до 19:00')).toEqual({ startTime: '11:00', endTime: '19:00' })
  })

  it('reads "from 10 to 6" as an afternoon end', () => {
    expect(extractTimeWindow('plan my day from 10 to 6')).toEqual({ startTime: '10:00', endTime: '18:00' })
  })

  it('drops an end time that is still before the start', () => {
    expect(extractTimeWindow('from 14:00 until 13:00')).toEqual({ startTime: '14:00' })
  })

  it('does not take a count of people for a start time', () => {
    expect(extractTimeWindow('план на день в Братиславе с 2 детьми')).toEqual({})
    expect(extractTimeWindow('plan a day out from 2 friends')).toEqual({})
  })

  it('honours am and pm on both ends', () => {
    expect(extractTimeWindow('Plan my day from 2pm until 6pm')).toEqual({ startTime: '14:00', endTime: '18:00' })
    expect(extractTimeWindow('from 9am to 1pm')).toEqual({ startTime: '09:00', endTime: '13:00' })
    expect(extractTimeWindow('from 9:30 a.m. until 5:15 p.m.')).toEqual({ startTime: '09:30', endTime: '17:15' })
    expect(extractTimeWindow('from 10 to 6pm')).toEqual({ startTime: '10:00', endTime: '18:00' })
  })

  it('maps 12am to midnight and 12pm to noon', () => {
    expect(extractTimeWindow('from 12pm until 5pm')).toEqual({ startTime: '12:00', endTime: '17:00' })
    expect(extractTimeWindow('starting at 12am')).toEqual({ startTime: '00:00' })
  })

  it('ignores impossible 12-hour times', () => {
    expect(extractTimeWindow('from 13pm')).toEqual({})
  })
})
