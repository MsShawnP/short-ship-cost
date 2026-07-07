import { useEffect, useRef, useState } from 'react'

const DURATION = 250
export const REDUCED_MOTION =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export default function useAnimatedValue(target, formatter) {
  const [display, setDisplay] = useState(() => formatter(target))
  const raf = useRef(null)
  const from = useRef(target)
  const isFirst = useRef(true)

  useEffect(() => {
    if (isFirst.current) {
      isFirst.current = false
      from.current = target
      setDisplay(formatter(target))
      return
    }

    if (REDUCED_MOTION || from.current === target) {
      from.current = target
      setDisplay(formatter(target))
      return
    }

    const start = from.current
    const delta = target - start
    const t0 = performance.now()

    function tick(now) {
      const elapsed = now - t0
      const progress = Math.min(elapsed / DURATION, 1)
      const eased = 1 - (1 - progress) ** 3
      const current = start + delta * eased
      setDisplay(formatter(current))
      if (progress < 1) {
        raf.current = requestAnimationFrame(tick)
      } else {
        from.current = target
      }
    }

    if (raf.current) cancelAnimationFrame(raf.current)
    raf.current = requestAnimationFrame(tick)

    return () => {
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [target, formatter])

  return display
}
