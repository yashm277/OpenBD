import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import {
  IconTrash,
  IconSearch,
  IconShuffle,
  IconMail,
  IconArrowUpRight,
  IconChevronRight,
} from '../components/Icons'

interface Tool {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  accent?: boolean
  title: string
  description: string
  href: string
  external?: boolean
  label: string
}

const tools: Tool[] = [
  {
    icon: IconTrash,
    title: 'Delete List Generator',
    description:
      'Upload email dump CSVs and automatically flag inactive addresses — those appearing in 3+ dumps with zero opens.',
    href: '/delete-list',
    label: 'Generate list →',
  },
  {
    icon: IconSearch,
    title: 'Duplicate Email Finder',
    description:
      'Identify duplicate entries across one or more CSVs — by email address, company name, or full name.',
    href: '/duplicate-finder',
    label: 'Find duplicates →',
  },
  {
    icon: IconShuffle,
    title: 'Overlap Checker',
    description:
      'Remove overlapping emails between two CSV datasets and download a clean, de-duplicated list instantly.',
    href: '/overlap-checker',
    label: 'Check overlap →',
  },
  {
    icon: IconMail,
    accent: true,
    title: 'Gmail Lead Analyzer',
    description:
      'Advanced lead intelligence, engagement tracking, and outreach automation via the RISE platform.',
    href: 'https://riseglobaleducation.com/',
    external: true,
    label: 'Open platform ↗',
  },
]

export default function Dashboard() {
  const navigate = useNavigate()

  function open(tool: Tool) {
    if (tool.external) window.open(tool.href, '_blank', 'noopener,noreferrer')
    else navigate(tool.href)
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      {/* Hero */}
      <div className="dash-hero">
        <div className="dash-hero-badge">
          RISE Research · Internal Tools
        </div>
        <h1>Data Management Suite</h1>
        <p>Clean, deduplicate, and analyze your contact lists in seconds — no code required.</p>
      </div>

      {/* Tools grid */}
      <div className="dash-body">
        <h2>Available Tools</h2>
        <div className="tools-grid">
          {tools.map(tool => {
            const Icon = tool.icon
            return (
              <div
                key={tool.title}
                className={`tool-card${tool.accent ? ' tools-grid-full' : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => open(tool)}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(tool) } }}
                style={tool.accent
                  ? { flexDirection: 'row', gap: 24, alignItems: 'center' }
                  : undefined}
              >
                <div className="tool-card-header">
                  <div className={`tool-card-icon-wrap${tool.accent ? ' brown' : ''}`}>
                    <Icon />
                  </div>
                  <div className="tool-card-arrow">
                    <IconArrowUpRight />
                  </div>
                </div>

                <div style={{ flex: 1 }}>
                  <h3>{tool.title}</h3>
                  <p>{tool.description}</p>
                  <div className={`tool-card-label${tool.accent ? ' ext' : ''}`}>
                    <IconChevronRight style={{ width: 12, height: 12 }} />
                    {tool.label}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <footer className="site-footer">© 2026 RISE Research — Internal Use Only</footer>
    </div>
  )
}

