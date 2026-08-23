/*
  Scan.tsx — upload a photo, or run one of the prepared demo products.

  About the progress steps: they follow the request, they are not a decorative
  timer. "Uploading" is true while the browser is sending bytes; "Reading the
  label" is true while we are waiting on the backend (which is where the Gemini
  call happens); the rest flip when the response lands. We cannot see inside the
  backend from here, so the middle stages are shown as one wait rather than
  faked as separate timed steps.
*/

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Check,
  FlaskConical,
  ImageUp,
  Info,
  Loader2,
  ScanLine,
  Sparkles,
  Upload,
  X,
} from 'lucide-react'
import { getDemoProducts, getHealth, scanDemoProduct, scanImage } from '../api'
import type { DemoProduct, Health } from '../types'
import { Band, Button, ErrorNote, SectionTitle, StatusBadge } from '../ui'

const STEPS = ['Uploading the image', 'Reading the label with AI', 'Running the 15 rule checks', 'Preparing the result']

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 10 * 1024 * 1024

function ProgressSteps({ activeStep }: { activeStep: number }) {
  return (
    <ol className="space-y-3">
      {STEPS.map((step, index) => {
        const done = index < activeStep
        const active = index === activeStep
        return (
          <li key={step} className="flex items-center gap-4">
            <span
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg font-bold transition-all duration-200 ${
                done ? 'bg-secondary text-white' : active ? 'bg-primary text-white' : 'bg-line text-gray-500'
              }`}
            >
              {done ? (
                <Check className="h-5 w-5" strokeWidth={3} />
              ) : active ? (
                <Loader2 className="h-5 w-5 animate-spin" strokeWidth={2.5} />
              ) : (
                index + 1
              )}
            </span>
            <span className={`font-semibold ${done || active ? 'text-ink' : 'text-gray-400'}`}>{step}</span>
          </li>
        )
      })}
    </ol>
  )
}

export default function Scan() {
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)

  const [health, setHealth] = useState<Health | null>(null)
  const [demoProducts, setDemoProducts] = useState<DemoProduct[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState<string | null>(null) // which action is running
  const [step, setStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null))
    getDemoProducts()
      .then(setDemoProducts)
      .catch((issue: Error) => setError(issue.message))
  }, [])

  // Release the object URL when the preview changes, so we do not leak it.
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  function chooseFile(chosen: File | undefined) {
    setError(null)
    if (!chosen) return

    if (!ACCEPTED.includes(chosen.type)) {
      setError('Please choose a JPG, PNG or WEBP image.')
      return
    }
    if (chosen.size > MAX_BYTES) {
      setError('That image is larger than 10 MB. Please choose a smaller photo.')
      return
    }

    if (preview) URL.revokeObjectURL(preview)
    setFile(chosen)
    setPreview(URL.createObjectURL(chosen))
  }

  function clearFile() {
    if (preview) URL.revokeObjectURL(preview)
    setFile(null)
    setPreview(null)
    if (fileInput.current) fileInput.current.value = ''
  }

  async function runUploadScan() {
    if (!file) return
    setBusy('upload')
    setError(null)
    setStep(0)

    try {
      // The request is in flight: the backend is now uploading, extracting and
      // checking. Step 1 covers the whole server-side wait.
      setStep(1)
      const response = await scanImage(file)
      setStep(3)
      navigate(`/result/${response.inspection.id}`)
    } catch (issue) {
      setError((issue as Error).message)
      setBusy(null)
      setStep(0)
    }
  }

  async function runDemoScan(id: string, live: boolean) {
    setBusy(`${id}-${live}`)
    setError(null)

    try {
      const response = await scanDemoProduct(id, live)
      navigate(`/result/${response.inspection.id}`)
    } catch (issue) {
      setError((issue as Error).message)
      setBusy(null)
    }
  }

  const aiOff = health !== null && !health.ai_configured

  return (
    <>
      <Band className="bg-primary text-white" decorated>
        <div className="max-w-3xl">
          <h1 className="text-4xl font-extrabold md:text-5xl">Scan a package</h1>
          <p className="mt-4 text-lg text-white/90">
            Upload a photograph of the label, or run one of the four prepared demo products. Both paths use the same
            rule engine.
          </p>
        </div>
      </Band>

      <Band>
        {error && (
          <div className="mb-8">
            <ErrorNote message={error} />
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-5">
          {/* ---------------- Upload ---------------- */}
          <div className="lg:col-span-3">
            <SectionTitle eyebrow="Live scan" title="Upload a photograph" />

            {aiOff && (
              <p className="mb-6 flex items-start gap-3 rounded-lg bg-accent-tint p-5 leading-relaxed text-accent-dark">
                <Info className="mt-0.5 h-5 w-5 shrink-0" strokeWidth={2.5} />
                <span>
                  <strong>No Gemini API key is configured</strong>, so a live scan will fail with a clear message. Add{' '}
                  <code className="rounded bg-white px-1.5 py-0.5 text-sm font-semibold">GEMINI_API_KEY</code> to{' '}
                  <code className="rounded bg-white px-1.5 py-0.5 text-sm font-semibold">.env</code> and restart the
                  backend. Demo Mode below needs no key.
                </span>
              </p>
            )}

            {busy === 'upload' ? (
              <div className="rounded-lg bg-muted p-8">
                <ProgressSteps activeStep={step} />
              </div>
            ) : (
              <>
                <div
                  onDragOver={(event) => {
                    event.preventDefault()
                    setDragging(true)
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(event) => {
                    event.preventDefault()
                    setDragging(false)
                    chooseFile(event.dataTransfer.files[0])
                  }}
                  className={`rounded-lg p-8 transition-all duration-200 ${
                    dragging ? 'bg-white ring-4 ring-primary' : 'bg-muted'
                  }`}
                >
                  {preview ? (
                    <div>
                      <img
                        src={preview}
                        alt="The package you are about to check"
                        className="mx-auto max-h-96 rounded-lg"
                      />
                      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
                        <p className="min-w-0 truncate text-sm font-semibold text-gray-600">
                          {file?.name} · {Math.round((file?.size ?? 0) / 1024)} KB
                        </p>
                        <button
                          onClick={clearFile}
                          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-gray-600 transition-all duration-200 hover:bg-line hover:text-ink"
                        >
                          <X className="h-4 w-4" strokeWidth={2.5} />
                          Choose a different image
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInput.current?.click()}
                      className="group flex w-full flex-col items-center gap-4 py-10 text-center"
                    >
                      <span className="flex h-16 w-16 items-center justify-center rounded-lg bg-primary">
                        <ImageUp
                          className="h-8 w-8 text-white transition-transform duration-200 group-hover:scale-110"
                          strokeWidth={2.5}
                        />
                      </span>
                      <span className="text-xl font-bold">Drop a label photo here, or click to browse</span>
                      <span className="text-sm text-gray-500">JPG, PNG or WEBP · up to 10 MB</span>
                    </button>
                  )}

                  <input
                    ref={fileInput}
                    type="file"
                    accept={ACCEPTED.join(',')}
                    className="hidden"
                    onChange={(event) => chooseFile(event.target.files?.[0])}
                  />
                </div>

                <div className="mt-6">
                  <Button onClick={runUploadScan} disabled={!file || busy !== null}>
                    <ScanLine className="h-5 w-5" strokeWidth={2.5} />
                    Check compliance
                  </Button>
                </div>
              </>
            )}
          </div>

          {/* ---------------- What gets checked ---------------- */}
          <aside className="rounded-lg bg-ink p-6 text-white md:p-8 lg:col-span-2">
            <h3 className="text-xl font-bold">What happens to your photo</h3>
            <ul className="mt-6 space-y-5 text-sm leading-relaxed text-gray-300">
              <li className="flex gap-3">
                <Upload className="mt-0.5 h-5 w-5 shrink-0 text-primary" strokeWidth={2.5} />
                <span>
                  It is saved locally in <code className="text-white">backend/uploads/</code> so the result page and the
                  PDF can show the evidence.
                </span>
              </li>
              <li className="flex gap-3">
                <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" strokeWidth={2.5} />
                <span>
                  It is sent to Gemini once, from the backend. The API key never reaches the browser. The model is
                  asked to report only what is printed and to leave anything it cannot see empty.
                </span>
              </li>
              <li className="flex gap-3">
                <FlaskConical className="mt-0.5 h-5 w-5 shrink-0 text-primary" strokeWidth={2.5} />
                <span>
                  The reading goes to the rule engine at temperature 0, so the same photo produces the same verdict
                  every time.
                </span>
              </li>
            </ul>
            {health && (
              <p className="mt-8 border-t-2 border-white/10 pt-6 text-xs tracking-wider text-gray-400 uppercase">
                Model: {health.model} · {health.rules_loaded} rules loaded
              </p>
            )}
          </aside>
        </div>
      </Band>

      {/* ---------------- Demo products ---------------- */}
      <Band className="bg-muted">
        <SectionTitle
          eyebrow="Demo mode · no API key needed"
          title="Four prepared products"
          lead="The label reading for each of these is cached, so the demo never depends on the network. Everything after the reading — the rule checks, the score, the database entry, the PDF — runs live."
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {demoProducts.map((product) => (
            <div key={product.id} className="flex flex-col rounded-lg bg-white p-6">
              {product.image_url ? (
                <img
                  src={product.image_url}
                  alt={`Label of the ${product.label} demo product`}
                  className="h-44 w-full rounded-lg object-cover object-top"
                />
              ) : (
                <div className="flex h-44 w-full items-center justify-center rounded-lg bg-muted p-4 text-center text-sm text-gray-500">
                  Run <code className="mx-1">generate_demo_images.py</code> to create this image
                </div>
              )}

              <h3 className="mt-5 text-lg font-bold">{product.label}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-gray-600">{product.description}</p>

              <p className="mt-5 text-xs font-semibold tracking-wider text-gray-500 uppercase">Expected verdict</p>
              <div className="mt-2">
                <StatusBadge status={product.expected_status} />
              </div>

              <button
                onClick={() => runDemoScan(product.id, false)}
                disabled={busy !== null}
                className="mt-5 flex h-12 items-center justify-center gap-2 rounded-lg bg-primary font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-primary-dark disabled:pointer-events-none disabled:opacity-50"
              >
                {busy === `${product.id}-false` ? (
                  <Loader2 className="h-5 w-5 animate-spin" strokeWidth={2.5} />
                ) : (
                  <ScanLine className="h-5 w-5" strokeWidth={2.5} />
                )}
                Run demo
              </button>

              {/* Only offered when a key exists: the same image, read for real. */}
              {health?.ai_configured && (
                <button
                  onClick={() => runDemoScan(product.id, true)}
                  disabled={busy !== null}
                  className="mt-2 flex h-12 items-center justify-center gap-2 rounded-lg border-4 border-primary font-semibold text-primary transition-all duration-200 hover:scale-105 hover:bg-primary hover:text-white disabled:pointer-events-none disabled:opacity-50"
                >
                  {busy === `${product.id}-true` ? (
                    <Loader2 className="h-5 w-5 animate-spin" strokeWidth={2.5} />
                  ) : (
                    <Sparkles className="h-5 w-5" strokeWidth={2.5} />
                  )}
                  Run live with Gemini
                </button>
              )}
            </div>
          ))}
        </div>
      </Band>
    </>
  )
}
