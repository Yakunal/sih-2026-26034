/*
  ui.tsx — the small shared pieces every page uses.

  Kept in one file on purpose: these are a few dozen lines each, and having the
  status colours defined exactly once is what stops the three pages from drifting
  apart. Bigger pieces live in their own files.
*/

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, HelpCircle, MinusCircle } from 'lucide-react'
import type { CheckResult, Source, Status } from './types'

/* ------------------------------------------------------------------ */
/* Status vocabulary — the single source of truth for how a verdict looks */
/* ------------------------------------------------------------------ */

export const STATUS_STYLE: Record<Status, { label: string; block: string; tint: string; text: string; Icon: typeof CheckCircle2 }> = {
  COMPLIANT: {
    label: 'Compliant',
    block: 'bg-secondary',
    tint: 'bg-secondary-tint',
    text: 'text-secondary-dark',
    Icon: CheckCircle2,
  },
  NEEDS_REVIEW: {
    label: 'Needs Review',
    block: 'bg-accent',
    tint: 'bg-accent-tint',
    text: 'text-accent-dark',
    Icon: HelpCircle,
  },
  POTENTIAL_VIOLATION: {
    label: 'Potential Violation',
    block: 'bg-danger',
    tint: 'bg-danger-tint',
    text: 'text-danger-dark',
    Icon: AlertTriangle,
  },
}

export const RESULT_STYLE: Record<CheckResult, { label: string; block: string; tint: string; text: string; Icon: typeof CheckCircle2 }> = {
  PASS: { label: 'Pass', block: 'bg-secondary', tint: 'bg-secondary-tint', text: 'text-secondary-dark', Icon: CheckCircle2 },
  FAIL: { label: 'Fail', block: 'bg-danger', tint: 'bg-danger-tint', text: 'text-danger-dark', Icon: AlertTriangle },
  REVIEW: { label: 'Needs physical check', block: 'bg-accent', tint: 'bg-accent-tint', text: 'text-accent-dark', Icon: HelpCircle },
  NOT_APPLICABLE: { label: 'Not applicable', block: 'bg-gray-400', tint: 'bg-muted', text: 'text-gray-500', Icon: MinusCircle },
}

/** How a result's origin is described wherever it appears. */
export const SOURCE_STYLE: Record<Source, { label: string; detail: string } | null> = {
  live_ai: null, // a real scan needs no caveat
  demo_cached: {
    label: 'Demo Result',
    detail:
      'The label reading for this product is cached, so the demo works without an API key. Everything after it — the rule checks, the score and this page — was computed live just now.',
  },
  seed: {
    label: 'Sample Data',
    detail:
      'This inspection was generated to populate the demo dashboard. It is not a real scan, though its rule results were computed by the real rule engine.',
  },
}

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */

type ButtonProps = {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'outline' | 'outlineLight'
  className?: string
}

const BUTTON_BASE =
  'inline-flex items-center justify-center gap-2 rounded-lg px-6 font-semibold ' +
  'transition-all duration-200 hover:scale-105 disabled:pointer-events-none disabled:opacity-50'

const BUTTON_VARIANT = {
  primary: 'h-14 bg-primary text-white hover:bg-primary-dark',
  secondary: 'h-14 bg-muted text-ink hover:bg-line',
  outline: 'h-14 border-4 border-primary text-primary hover:bg-primary hover:text-white',
  outlineLight: 'h-14 border-4 border-white text-white hover:bg-white hover:text-primary',
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...rest
}: ButtonProps & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={`${BUTTON_BASE} ${BUTTON_VARIANT[variant]} ${className}`} {...rest}>
      {children}
    </button>
  )
}

export function ButtonLink({
  children,
  to,
  variant = 'primary',
  className = '',
}: ButtonProps & { to: string }) {
  return (
    <Link to={to} className={`${BUTTON_BASE} ${BUTTON_VARIANT[variant]} ${className}`}>
      {children}
    </Link>
  )
}

/* ------------------------------------------------------------------ */
/* Badges, cards and page furniture                                    */
/* ------------------------------------------------------------------ */

export function StatusBadge({ status, className = '' }: { status: Status; className?: string }) {
  const { label, tint, text, Icon } = STATUS_STYLE[status]
  return (
    <span className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold ${tint} ${text} ${className}`}>
      <Icon className="h-4 w-4" strokeWidth={2.5} />
      {label}
    </span>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg bg-muted p-6 md:p-8 ${className}`}>{children}</div>
}

export function SectionTitle({ eyebrow, title, lead }: { eyebrow?: string; title: string; lead?: string }) {
  return (
    <div className="mb-8">
      {eyebrow && <p className="mb-2 text-sm font-semibold tracking-wider text-primary uppercase">{eyebrow}</p>}
      <h2 className="text-3xl font-extrabold md:text-4xl">{title}</h2>
      {lead && <p className="mt-3 max-w-3xl text-lg text-gray-600">{lead}</p>}
    </div>
  )
}

/** A full-width flat colour block, the design system's main structural device. */
export function Band({
  children,
  className = '',
  decorated = false,
}: {
  children: ReactNode
  className?: string
  decorated?: boolean
}) {
  return (
    <section className={`relative overflow-hidden ${className}`}>
      {decorated && (
        // Large low-opacity geometry: visual interest with no depth.
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -top-32 -right-24 h-96 w-96 rounded-full bg-white/10" />
          <div className="absolute -top-10 right-40 h-56 w-56 rounded-full border-8 border-white/10" />
          <div className="absolute -bottom-28 -left-20 h-80 w-80 rotate-12 rounded-lg bg-white/5" />
        </div>
      )}
      <div className="relative mx-auto max-w-7xl px-6 py-16 md:py-20">{children}</div>
    </section>
  )
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-4 border-white/40 border-t-white ${className}`}
      aria-hidden
    />
  )
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-lg bg-danger-tint p-6">
      <p className="flex items-start gap-3 font-semibold text-danger-dark">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" strokeWidth={2.5} />
        {message}
      </p>
    </div>
  )
}

/** Formats the ISO timestamps the backend stores. */
export function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
