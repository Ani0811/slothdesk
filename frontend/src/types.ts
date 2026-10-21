export type Category =
  | 'Documents'
  | 'Images'
  | 'Videos'
  | 'Audio'
  | 'Archives'
  | 'Code'
  | 'Other'

export interface FileItem {
  filename: string
  relative_path: string
  size_bytes: number
  extension: string
  mtime: number
  sha256: string
  detected_category?: Category | string
}

export interface FilesInventoryResponse {
  root_directory: string
  total_files: number
  total_size_bytes: number
  files: FileItem[]
}

export interface PlannedOperation {
  source_rel_path: string
  dest_rel_path: string
  category: Category
  reason: string
  file_size: number
  expected_sha256: string
  expected_mtime: number
  has_collision: boolean
  collision_warning?: string | null
}

export interface SkippedItem {
  source_rel_path: string
  reason: string
}

export interface PlanResponse {
  plan_id: string
  created_at: string
  expires_at: string
  total_files_scanned: number
  total_size_bytes: number
  operations_count: number
  operations: PlannedOperation[]
  skipped: SkippedItem[]
  model_mode: 'local_ai_smolagents' | 'deterministic_fallback'
  model_name: string
  warnings: string[]
}

export interface ExecutionMoveResult {
  source_rel_path: string
  dest_rel_path: string
  status: 'moved' | 'skipped' | 'failed'
  size_bytes: number
  sha256: string
  error?: string | null
}

export interface ExecutionManifest {
  manifest_id: string
  plan_id: string
  timestamp: string
  total_attempted: number
  total_succeeded: number
  total_skipped: number
  total_failed: number
  status: 'completed' | 'partially_completed' | 'failed'
  undo_status: 'ready' | 'undone' | 'partially_undone' | 'failed'
  completed_moves: ExecutionMoveResult[]
  skipped_moves: ExecutionMoveResult[]
  failed_moves: ExecutionMoveResult[]
  undone_moves: Array<{ path: string; timestamp: string }>
  undo_failures: Array<{ source?: string; dest?: string; reason: string }>
}

export interface ExecutionResponse {
  manifest_id: string
  plan_id: string
  timestamp: string
  status: 'completed' | 'partially_completed' | 'failed'
  total_moved: number
  total_skipped: number
  total_failed: number
  completed_moves: ExecutionMoveResult[]
  skipped_moves: ExecutionMoveResult[]
  failed_moves: ExecutionMoveResult[]
}

export interface UndoResponse {
  manifest_id: string
  status: 'undone' | 'partially_undone' | 'failed'
  restored_count: number
  failed_count: number
  details: Array<Record<string, unknown>>
}

export interface HealthResponse {
  status: string
  backend: string
  slothdesk_root: string
  lm_studio_connected: boolean
  lm_studio_model: string
  available_models: string[]
  ai_classification_available: boolean
  deterministic_fallback_active: boolean
  total_manifests: number
}
