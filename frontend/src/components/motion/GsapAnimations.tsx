"use client"

import { useRef } from "react"
import gsap from "gsap"
import { useGSAP } from "@gsap/react"

gsap.registerPlugin(useGSAP)

interface FadeInProps {
  children: React.ReactNode
  className?: string
  delay?: number
  y?: number
}

export function FadeIn({
  children,
  className,
  delay = 0,
  y = 24,
}: FadeInProps) {
  const ref = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      gsap.from(ref.current, {
        autoAlpha: 0,
        y,
        duration: 0.7,
        delay,
        ease: "power3.out",
      })
    },
    { scope: ref },
  )

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  )
}

interface StaggerChildrenProps {
  children: React.ReactNode
  className?: string
  selector?: string
}

export function StaggerChildren({
  children,
  className,
  selector = ".stagger-item",
}: StaggerChildrenProps) {
  const ref = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      gsap.from(selector, {
        autoAlpha: 0,
        y: 20,
        scale: 0.98,
        duration: 0.55,
        stagger: 0.08,
        ease: "power2.out",
      })
    },
    { scope: ref },
  )

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  )
}

interface ScoreRevealProps {
  score: number
  className?: string
}

export function ScoreReveal({ score, className }: ScoreRevealProps) {
  const ref = useRef<HTMLSpanElement>(null)

  useGSAP(
    () => {
      const obj = { val: 0 }
      gsap.to(obj, {
        val: score,
        duration: 1.4,
        ease: "power2.out",
        onUpdate: () => {
          if (ref.current) {
            ref.current.textContent = obj.val.toFixed(1)
          }
        },
      })
    },
    { scope: ref, dependencies: [score], revertOnUpdate: true },
  )

  return <span ref={ref} className={className}>0.0</span>
}
