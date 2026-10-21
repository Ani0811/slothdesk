import { useState, useEffect } from 'react'
import {
  Folder,
  Cpu,
  RefreshCw,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Image,
  Video,
  Music,
  Archive,
  Code2,
  HelpCircle,
  ShieldCheck,
  Search,
  Check,
  X,
  History,
  Layers,
  Sparkles,
} from 'lucide-react'
import type {
  HealthResponse,
  FilesInventoryResponse,
  PlanResponse,
  ExecutionResponse,
  ExecutionManifest,
  FileItem,
  Category,
} from './types'
import {
  fetchHealth,
  fetchFiles,
  createPlan,
  executePlan,
  fetchUndoHistory,
  undoManifest,
} from './api'
import './style.css'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getCategoryIcon(cat: Category | string) {
  switch (cat) {
    case 'Documents':
      return <FileText size={16} className="text-sky-400" />
    case 'Images':
      return <Image size={16} className="text-emerald-400" />
    case 'Videos':
      return <Video size={16} className="text-purple-400" />
    case 'Audio':
      return <Music size={16} className="text-pink-400" />
    case 'Archives':
      return <Archive size={16} className="text-amber-400" />
    case 'Code':
      return <Code2 size={16} className="text-lime-400" />
    default:
      return <HelpCircle size={16} className="text-slate-400" />
  }
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [inventory, setInventory] = useState<FilesInventoryResponse | null>(null)
  const [activePlan, setActivePlan] = useState<PlanResponse | null>(null)
  const [manifests, setManifests] = useState<ExecutionManifest[]>([])
  const [activeTab, setActiveTab] = useState<'plan' | 'inventory' | 'history'>('plan')

  const [loadingHealth, setLoadingHealth] = useState(false)
  const [proposingPlan, setProposingPlan] = useState(false)
  const [executingPlan, setExecutingPlan] = useState(false)
  const [undoingId, setUndoingId] = useState<string | null>(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [showApprovalModal, setShowApprovalModal] = useState(false)
  const [lastExecution, setLastExecution] = useState<ExecutionResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Initial load
  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoadingHealth(true)
    try {
      const h = await fetchHealth()
      setHealth(h)
    } catch {
      // Backend not yet reachable
    } finally {
      setLoadingHealth(false)
    }

    try {
      const f = await fetchFiles()
      setInventory(f)
    } catch {
      //
    }

    try {
      const m = await fetchUndoHistory()
      setManifests(m)
    } catch {
      //
    }
  }

  async function handleScanAndPropose() {
    setProposingPlan(true)
    setErrorMessage(null)
    setLastExecution(null)
    try {
      const plan = await createPlan()
      setActivePlan(plan)
      setActiveTab('plan')
      // Refresh inventory and health
      const [f, h] = await Promise.all([fetchFiles(), fetchHealth()])
      setInventory(f)
      setHealth(h)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMessage(msg)
    } finally {
      setProposingPlan(false)
    }
  }

  async function handleConfirmExecution() {
    if (!activePlan) return
    setExecutingPlan(true)
    setErrorMessage(null)
    try {
      const report = await executePlan(activePlan.plan_id)
      setLastExecution(report)
      setActivePlan(null)
      setShowApprovalModal(false)

      // Refresh data
      const [f, h, m] = await Promise.all([fetchFiles(), fetchHealth(), fetchUndoHistory()])
      setInventory(f)
      setHealth(h)
      setManifests(m)
      setActiveTab('history')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMessage(msg)
    } finally {
      setExecutingPlan(false)
    }
  }

  async function handleUndo(manifestId: string) {
    setUndoingId(manifestId)
    setErrorMessage(null)
    try {
      await undoManifest(manifestId)
      // Refresh data
      const [f, h, m] = await Promise.all([fetchFiles(), fetchHealth(), fetchUndoHistory()])
      setInventory(f)
      setHealth(h)
      setManifests(m)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMessage(msg)
    } finally {
      setUndoingId(null)
    }
  }

  const filteredInventoryFiles = (inventory?.files || []).filter((f: FileItem) =>
    f.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <span className="brand-icon" role="img" aria-label="Sloth">
            🦥
          </span>
          <div>
            <span className="brand-title">SlothDesk</span>
            <span className="brand-tag">v0.1.0</span>
          </div>
        </div>

        <div className="header-status-group">
          {/* AI Model Status Badge */}
          {health?.lm_studio_connected ? (
            <div className="status-pill connected" title="LM Studio is online and active">
              <span className="pulse-dot" />
              <Cpu size={14} />
              <span>
                Local AI: <strong>{health.lm_studio_model}</strong>
              </span>
            </div>
          ) : (
            <div
              className="status-pill fallback"
              title="LM Studio offline; using deterministic classification fallback"
            >
              <span className="pulse-dot" />
              <Cpu size={14} />
              <span>
                Deterministic Fallback Mode <em>(LM Studio Offline)</em>
              </span>
            </div>
          )}

          {/* Root Directory Pill */}
          <div className="status-pill root-pill" title={`Root: ${health?.slothdesk_root || 'Loading...'}`}>
            <Folder size={14} />
            <span>{health?.slothdesk_root || 'Managed Downloads'}</span>
          </div>

          <button
            className="btn-secondary"
            onClick={loadAll}
            disabled={loadingHealth}
            title="Refresh workspace status"
          >
            <RefreshCw size={14} className={loadingHealth ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Hero Card */}
      <section className="hero-card">
        <div className="hero-content">
          <h1>Effortless Downloads Organizer</h1>
          <p className="hero-tagline">Less sorting. More living.</p>
          <p className="hero-description">
            SlothDesk tidies your cluttered Downloads folder using local-first AI and safe,
            two-phase execution. Inspect every proposed relocation, approve moves with a single
            click, and undo anytime with immutable manifests.
          </p>
        </div>

        <div className="hero-actions">
          <button
            id="scan-propose-btn"
            className="btn-primary"
            onClick={handleScanAndPropose}
            disabled={proposingPlan}
          >
            {proposingPlan ? (
              <>
                <RefreshCw size={18} className="spin" />
                Scanning &amp; Reasoning...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Scan &amp; Propose Plan
              </>
            )}
          </button>

          <div className="read-only-badge">
            <ShieldCheck size={14} className="text-lime-400" />
            <span>Scanning is strictly read-only</span>
          </div>
        </div>
      </section>

      {/* Error Banner */}
      {errorMessage && (
        <div className="alert-card warning">
          <div className="alert-content">
            <AlertTriangle size={20} />
            <div>
              <strong>Action notice:</strong> {errorMessage}
            </div>
          </div>
          <button className="btn-secondary" onClick={() => setErrorMessage(null)}>
            Dismiss
          </button>
        </div>
      )}

      {/* Execution Success Banner */}
      {lastExecution && (
        <div className="alert-card success">
          <div className="alert-content">
            <CheckCircle2 size={22} />
            <div>
              <strong>Execution successful!</strong> Moved{' '}
              <strong>{lastExecution.total_moved}</strong> files into categorized folders.
              <div style={{ fontSize: '12px', marginTop: '2px', opacity: 0.9 }}>
                Audit Manifest ID: <code>{lastExecution.manifest_id}</code>
              </div>
            </div>
          </div>
          <button
            className="btn-secondary"
            onClick={() => handleUndo(lastExecution.manifest_id)}
            disabled={undoingId === lastExecution.manifest_id}
          >
            <RotateCcw size={14} />
            {undoingId === lastExecution.manifest_id ? 'Undoing...' : 'Undo this Move'}
          </button>
        </div>
      )}

      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <Folder size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Files Scanned</span>
            <span className="stat-value">{inventory?.total_files ?? 0}</span>
            <span className="stat-subtext">Direct top-level files</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Layers size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Total Size</span>
            <span className="stat-value">{formatBytes(inventory?.total_size_bytes ?? 0)}</span>
            <span className="stat-subtext">Across root items</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Sparkles size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Proposed Moves</span>
            <span className="stat-value">{activePlan?.operations_count ?? 0}</span>
            <span className="stat-subtext">
              {activePlan ? `${activePlan.model_mode === 'local_ai_smolagents' ? 'Local AI' : 'Deterministic'}` : 'Awaiting scan'}
            </span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <History size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-label">Saved Manifests</span>
            <span className="stat-value">{manifests.length}</span>
            <span className="stat-subtext">Reversible operations</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === 'plan' ? 'active' : ''}`}
          onClick={() => setActiveTab('plan')}
        >
          <Sparkles size={16} />
          Proposed Plan
          {activePlan && <span className="tab-badge">{activePlan.operations_count}</span>}
        </button>

        <button
          className={`tab-btn ${activeTab === 'inventory' ? 'active' : ''}`}
          onClick={() => setActiveTab('inventory')}
        >
          <Folder size={16} />
          Downloads Inventory
          {inventory && <span className="tab-badge">{inventory.total_files}</span>}
        </button>

        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <History size={16} />
          History &amp; Undo
          <span className="tab-badge">{manifests.length}</span>
        </button>
      </nav>

      {/* TAB 1: Proposed Plan */}
      {activeTab === 'plan' && (
        <section className="content-card">
          <div className="card-header-bar">
            <div className="card-title-group">
              <h2>
                <Sparkles size={20} className="text-lime-400" />
                Proposed Organization Plan
              </h2>
              <p className="card-subtitle">
                Review proposed moves before execution. SlothDesk will never overwrite existing
                files.
              </p>
            </div>

            {activePlan && activePlan.operations_count > 0 && (
              <button
                id="review-execute-btn"
                className="btn-primary"
                onClick={() => setShowApprovalModal(true)}
              >
                <Play size={16} />
                Review &amp; Approve Execution ({activePlan.operations_count})
              </button>
            )}
          </div>

          {activePlan ? (
            <>
              <div className="plan-banner">
                <div className="plan-banner-meta">
                  <div className="plan-meta-item">
                    <strong>Plan ID:</strong> <code>{activePlan.plan_id}</code>
                  </div>
                  <div className="plan-meta-item">
                    <strong>Inference:</strong>{' '}
                    <span className="badge badge-code">
                      {activePlan.model_mode === 'local_ai_smolagents'
                        ? `smolagents + ${activePlan.model_name}`
                        : 'Deterministic Rule Fallback'}
                    </span>
                  </div>
                  {activePlan.warnings.length > 0 && (
                    <div className="plan-meta-item">
                      <span className="collision-tag">
                        <AlertTriangle size={12} />
                        {activePlan.warnings.length} collision(s) safely resolved
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {activePlan.operations.length > 0 ? (
                <div className="table-responsive">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Source File</th>
                        <th>Category</th>
                        <th>Target Destination</th>
                        <th>Size</th>
                        <th>Reasoning &amp; Safety</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activePlan.operations.map((op, idx) => (
                        <tr key={idx}>
                          <td>
                            <div className="file-name-cell">
                              {getCategoryIcon(op.category)}
                              <span>{op.source_rel_path}</span>
                            </div>
                          </td>
                          <td>
                            <span className={`badge badge-${op.category.toLowerCase()}`}>
                              {op.category}
                            </span>
                          </td>
                          <td>
                            <span className="path-code">{op.dest_rel_path}</span>
                          </td>
                          <td>{formatBytes(op.file_size)}</td>
                          <td>
                            <div style={{ fontSize: '12px' }}>
                              <span>{op.reason}</span>
                              {op.has_collision && (
                                <div style={{ marginTop: '4px' }}>
                                  <span className="collision-tag">
                                    <AlertTriangle size={12} />
                                    {op.collision_warning}
                                  </span>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">
                  <CheckCircle2 size={36} className="text-lime-400" />
                  <h3>Folder is already organized!</h3>
                  <p>No loose files found in root requiring organization.</p>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <Sparkles size={40} className="empty-icon" />
              <h3>No Active Proposal</h3>
              <p>Click "Scan &amp; Propose Plan" above to analyze your Downloads folder.</p>
            </div>
          )}
        </section>
      )}

      {/* TAB 2: Downloads Inventory */}
      {activeTab === 'inventory' && (
        <section className="content-card">
          <div className="card-header-bar">
            <div className="card-title-group">
              <h2>
                <Folder size={20} className="text-lime-400" />
                Current Files Inventory
              </h2>
              <p className="card-subtitle">
                Inspect files residing directly in the configured Downloads root directory.
              </p>
            </div>

            <div style={{ position: 'relative', width: '260px' }}>
              <Search
                size={16}
                style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }}
              />
              <input
                type="text"
                placeholder="Filter files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px 8px 34px',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                }}
              />
            </div>
          </div>

          {filteredInventoryFiles.length > 0 ? (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Detected Category</th>
                    <th>Size</th>
                    <th>Extension</th>
                    <th>SHA-256 (Verification Hash)</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInventoryFiles.map((file, idx) => (
                    <tr key={idx}>
                      <td>
                        <div className="file-name-cell">
                          {getCategoryIcon(file.detected_category || 'Other')}
                          <span>{file.filename}</span>
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge badge-${(file.detected_category || 'other').toLowerCase()}`}
                        >
                          {file.detected_category || 'Other'}
                        </span>
                      </td>
                      <td>{formatBytes(file.size_bytes)}</td>
                      <td>
                        <code>{file.extension || 'none'}</code>
                      </td>
                      <td>
                        <code
                          style={{
                            fontSize: '11px',
                            color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {file.sha256 ? `${file.sha256.slice(0, 12)}...` : 'not computed'}
                        </code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <Folder size={40} className="empty-icon" />
              <h3>No matching files found</h3>
              <p>Your managed Downloads directory has no top-level loose files matching the search.</p>
            </div>
          )}
        </section>
      )}

      {/* TAB 3: History & Undo */}
      {activeTab === 'history' && (
        <section className="content-card">
          <div className="card-header-bar">
            <div className="card-title-group">
              <h2>
                <History size={20} className="text-lime-400" />
                Execution History &amp; Reversible Manifests
              </h2>
              <p className="card-subtitle">
                Every execution generates an immutable JSON audit manifest. Click Undo to restore
                files.
              </p>
            </div>
          </div>

          {manifests.length > 0 ? (
            <div className="manifest-list">
              {manifests.map((m) => (
                <div key={m.manifest_id} className="manifest-card">
                  <div className="manifest-info">
                    <div className="manifest-header">
                      <span className="manifest-id">{m.manifest_id}</span>
                      <span
                        className={`badge ${
                          m.undo_status === 'undone'
                            ? 'badge-other'
                            : m.status === 'completed'
                            ? 'badge-code'
                            : 'badge-archives'
                        }`}
                      >
                        {m.undo_status === 'undone' ? 'Reverted' : m.status}
                      </span>
                      <span className="manifest-time">
                        {new Date(m.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="manifest-stats">
                      Moved <strong>{m.total_succeeded}</strong> files
                      {m.total_skipped > 0 && ` • Skipped ${m.total_skipped}`}
                      {m.total_failed > 0 && ` • Failed ${m.total_failed}`}
                    </div>
                  </div>

                  <div className="manifest-actions">
                    {m.undo_status !== 'undone' ? (
                      <button
                        className="btn-secondary"
                        onClick={() => handleUndo(m.manifest_id)}
                        disabled={undoingId === m.manifest_id}
                      >
                        <RotateCcw size={14} />
                        {undoingId === m.manifest_id ? 'Restoring...' : 'Undo Operation'}
                      </button>
                    ) : (
                      <span
                        style={{
                          fontSize: '12px',
                          color: 'var(--text-muted)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <Check size={14} className="text-lime-400" />
                        Restored to original paths
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <History size={40} className="empty-icon" />
              <h3>No Past Operations Yet</h3>
              <p>When you approve and execute a plan, the execution manifest will appear here.</p>
            </div>
          )}
        </section>
      )}

      {/* Explicit Approval Modal Dialog */}
      {showApprovalModal && activePlan && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-dialog">
            <div className="modal-header">
              <div className="modal-title">
                <ShieldCheck size={24} className="text-lime-400" />
                Explicit Approval Required
              </div>
              <button
                className="btn-secondary"
                style={{ padding: '6px' }}
                onClick={() => setShowApprovalModal(false)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p>
                You are about to organize <strong>{activePlan.operations_count}</strong> files inside
                your configured Downloads directory:
              </p>

              <div className="safety-check-box">
                <div className="safety-check-item">
                  <Check size={16} className="text-lime-400" />
                  <span>Files will be organized directly into category subfolders</span>
                </div>
                <div className="safety-check-item">
                  <Check size={16} className="text-lime-400" />
                  <span>Zero files will be deleted</span>
                </div>
                <div className="safety-check-item">
                  <Check size={16} className="text-lime-400" />
                  <span>Zero files will be overwritten (collision safe rename applied)</span>
                </div>
                <div className="safety-check-item">
                  <Check size={16} className="text-lime-400" />
                  <span>Every move is reversible via an immutable manifest</span>
                </div>
              </div>

              {activePlan.warnings.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <span className="collision-tag">
                    <AlertTriangle size={14} />
                    {activePlan.warnings.length} Collision Notice(s):
                  </span>
                  <ul
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      marginTop: '6px',
                      paddingLeft: '20px',
                    }}
                  >
                    {activePlan.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowApprovalModal(false)}
                disabled={executingPlan}
              >
                Cancel
              </button>

              <button
                id="confirm-execute-btn"
                className="btn-primary"
                onClick={handleConfirmExecution}
                disabled={executingPlan}
              >
                {executingPlan ? (
                  <>
                    <RefreshCw size={16} className="spin" />
                    Executing Moves...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={16} />
                    Confirm &amp; Execute Moves
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
