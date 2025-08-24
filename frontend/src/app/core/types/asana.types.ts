export enum AsanaIntegrationStatus {
  INACTIVE = 'inactive',
  ACTIVE = 'active',
  ERROR = 'error',
  PENDING = 'pending'
}

export enum AsanaTaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped'
}

export interface AsanaWorkspace {
  gid: string;
  name: string;
  is_organization: boolean;
}

export interface AsanaProject {
  gid: string;
  name: string;
  notes?: string;
  workspace: AsanaWorkspace;
  color?: string;
  current_status?: {
    color: string;
    text: string;
    title: string;
  };
}

export interface AsanaUser {
  gid: string;
  name: string;
  email?: string;
  photo?: {
    image_60x60?: string;
  };
}

export interface AsanaTask {
  gid: string;
  name: string;
  notes?: string;
  assignee?: AsanaUser;
  completed: boolean;
  completed_at?: string;
  created_at: string;
  due_at?: string;
  due_on?: string;
  modified_at: string;
  projects: AsanaProject[];
  tags: Array<{
    gid: string;
    name: string;
    color?: string;
  }>;
  custom_fields?: Array<{
    gid: string;
    name: string;
    type: string;
    number_value?: number;
    text_value?: string;
    enum_value?: {
      gid: string;
      name: string;
      color?: string;
    };
  }>;
}

export interface AsanaIntegration {
  id: string;
  user_id: string;
  access_token: string;
  refresh_token?: string;
  token_expires_at?: string;
  workspace_gid: string;
  workspace_name: string;
  status: AsanaIntegrationStatus;
  last_sync_at?: string;
  last_error?: string;
  sync_interval_hours: number;
  auto_sync_enabled: boolean;
  created_at: string;
  updated_at: string;
  
  // Configuration
  pending_project_gid?: string;
  processed_project_gid?: string;
  default_assignee_gid?: string;
  expense_tag_gids: string[];
  income_tag_gids: string[];
  budget_custom_field_gid?: string;
  amount_custom_field_gid?: string;
  category_custom_field_gid?: string;
  sync_completed_tasks: boolean;
  create_transactions_from_tasks: boolean;
  archive_processed_tasks: boolean;
}

export interface AsanaTaskMapping {
  id: string;
  integration_id: string;
  task_gid: string;
  transaction_id?: string;
  status: AsanaTaskStatus;
  task_name: string;
  task_notes?: string;
  extracted_amount?: number;
  extracted_category?: string;
  extraction_confidence?: number;
  last_processed_at?: string;
  processing_errors?: string[];
  created_at: string;
  updated_at: string;
}

export interface AsanaWebhookEvent {
  action: string;
  change: {
    action: string;
    field?: string;
    new_value?: any;
    old_value?: any;
  };
  parent?: {
    gid: string;
    resource_type: string;
  };
  resource: {
    gid: string;
    resource_type: string;
  };
  user?: AsanaUser;
  created_at: string;
}

export interface AsanaWebhookPayload {
  events: AsanaWebhookEvent[];
}

// API Request/Response types
export interface AsanaIntegrationConfigRequest {
  workspace_gid: string;
  pending_project_gid?: string;
  processed_project_gid?: string;
  default_assignee_gid?: string;
  expense_tag_gids?: string[];
  income_tag_gids?: string[];
  budget_custom_field_gid?: string;
  amount_custom_field_gid?: string;
  category_custom_field_gid?: string;
  sync_interval_hours?: number;
  auto_sync_enabled?: boolean;
  sync_completed_tasks?: boolean;
  create_transactions_from_tasks?: boolean;
  archive_processed_tasks?: boolean;
}

export interface AsanaIntegrationResponse {
  integration: AsanaIntegration;
  workspaces: AsanaWorkspace[];
  projects: AsanaProject[];
  users: AsanaUser[];
}

export interface AsanaTaskMappingCreateRequest {
  task_gid: string;
  transaction_id?: string;
  force_reprocess?: boolean;
}

export interface AsanaTaskMappingResponse {
  mapping: AsanaTaskMapping;
  task: AsanaTask;
  transaction?: any;
}

export interface AsanaSyncRequest {
  force_full_sync?: boolean;
  specific_projects?: string[];
  sync_completed_tasks?: boolean;
}

export interface AsanaSyncResponse {
  sync_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  tasks_processed: number;
  transactions_created: number;
  errors: string[];
  summary: {
    new_tasks: number;
    updated_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    skipped_tasks: number;
  };
}

// OAuth types
export interface AsanaOAuthConfig {
  client_id: string;
  redirect_uri: string;
  response_type: 'code';
  state: string;
  code_challenge_method?: 'S256';
  code_challenge?: string;
}

export interface AsanaOAuthToken {
  access_token: string;
  token_type: string;
  expires_in?: number;
  refresh_token?: string;
  data?: {
    gid: string;
    name: string;
    email: string;
  };
}

// UI State types
export interface AsanaIntegrationState {
  integration: AsanaIntegration | null;
  workspaces: AsanaWorkspace[];
  projects: AsanaProject[];
  users: AsanaUser[];
  taskMappings: AsanaTaskMapping[];
  syncHistory: AsanaSyncResponse[];
  isLoading: boolean;
  isConfiguring: boolean;
  isSyncing: boolean;
  error: string | null;
  oauthInProgress: boolean;
}

export interface AsanaConfigurationForm {
  workspace_gid: string;
  pending_project_gid: string;
  processed_project_gid: string;
  default_assignee_gid: string;
  expense_tag_gids: string[];
  income_tag_gids: string[];
  budget_custom_field_gid: string;
  amount_custom_field_gid: string;
  category_custom_field_gid: string;
  sync_interval_hours: number;
  auto_sync_enabled: boolean;
  sync_completed_tasks: boolean;
  create_transactions_from_tasks: boolean;
  archive_processed_tasks: boolean;
}