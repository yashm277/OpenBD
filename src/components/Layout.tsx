import { useNavigate } from 'react-router-dom'
import Navbar from './Navbar'
import { IconChevronRight } from './Icons'

interface LayoutProps {
  title: string
  description: string
  children: React.ReactNode
}

export default function Layout({ title, description, children }: LayoutProps) {
  const navigate = useNavigate()

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <div className="page-header">
        <div className="page-header-inner">
          <div className="breadcrumb">
            <a onClick={() => navigate('/')}>Home</a>
            <span className="breadcrumb-sep">
              <IconChevronRight />
            </span>
            <span style={{ color: 'rgba(255,255,255,0.8)' }}>{title}</span>
          </div>
          <h1>{title}</h1>
          <p className="page-header-desc">{description}</p>
        </div>
      </div>

      <div className="page-body" style={{ flex: 1 }}>
        {children}
      </div>

      <footer className="site-footer">© 2026 RISE Research — Internal Tools</footer>
    </div>
  )
}

