import type { ReactNode } from 'react'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '20px 16px' }}>
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, color: '#4cc9f0' }}>LuxAuth Capture Workbench</h1>
        <p style={{ fontSize: 12, color: '#8892a4', marginTop: 4 }}>
          Local operator tooling — not production authentication
        </p>
      </header>
      {children}
    </div>
  )
}
