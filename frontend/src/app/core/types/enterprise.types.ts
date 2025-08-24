/**
 * Enterprise features types for Financial Nomad
 */

// Reports and Analytics Types
export interface ReportConfiguration {
  id: string;
  name: string;
  description: string;
  type: 'financial_summary' | 'transaction_analysis' | 'budget_performance' | 'category_breakdown' | 'custom';
  format: 'pdf' | 'excel' | 'csv';
  parameters: ReportParameters;
  schedule?: ReportSchedule;
  created_at: string;
  updated_at: string;
}

export interface ReportParameters {
  date_range: {
    start_date: string;
    end_date: string;
  };
  accounts?: string[];
  categories?: string[];
  transaction_types?: string[];
  include_charts: boolean;
  group_by?: 'day' | 'week' | 'month' | 'quarter' | 'year';
}

export interface ReportSchedule {
  enabled: boolean;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  day_of_week?: number;
  day_of_month?: number;
  time: string;
  recipients: string[];
}

export interface ReportExecution {
  id: string;
  report_id: string;
  status: 'queued' | 'generating' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  file_url?: string;
  error_message?: string;
  file_size?: number;
  pages?: number;
}

// Analytics Types
export interface FinancialInsights {
  spending_trends: SpendingTrend[];
  budget_analysis: BudgetAnalysis;
  category_insights: CategoryInsight[];
  predictions: FinancialPrediction[];
  anomalies: TransactionAnomaly[];
  recommendations: FinancialRecommendation[];
}

export interface SpendingTrend {
  period: string;
  total_spending: number;
  total_income: number;
  net_change: number;
  category_breakdown: CategorySpending[];
  trend_direction: 'up' | 'down' | 'stable';
  percentage_change: number;
}

export interface CategorySpending {
  category_id: string;
  category_name: string;
  amount: number;
  percentage_of_total: number;
  transactions_count: number;
}

export interface BudgetAnalysis {
  total_budgeted: number;
  total_spent: number;
  utilization_percentage: number;
  categories: BudgetCategoryAnalysis[];
  projected_end_of_month: ProjectedBudget;
}

export interface BudgetCategoryAnalysis {
  category_id: string;
  category_name: string;
  budgeted: number;
  spent: number;
  remaining: number;
  utilization_percentage: number;
  status: 'under_budget' | 'on_track' | 'over_budget' | 'warning';
}

export interface ProjectedBudget {
  projected_spending: number;
  projected_variance: number;
  confidence_level: number;
  risk_factors: string[];
}

export interface CategoryInsight {
  category_id: string;
  category_name: string;
  average_monthly_spending: number;
  trend_direction: 'increasing' | 'decreasing' | 'stable';
  seasonal_patterns: SeasonalPattern[];
  top_merchants: MerchantSpending[];
}

export interface SeasonalPattern {
  month: number;
  average_amount: number;
  transaction_count: number;
}

export interface MerchantSpending {
  merchant: string;
  amount: number;
  transaction_count: number;
  percentage_of_category: number;
}

export interface FinancialPrediction {
  type: 'spending_forecast' | 'income_forecast' | 'budget_projection' | 'savings_goal';
  category?: string;
  predicted_amount: number;
  confidence_interval: {
    lower: number;
    upper: number;
  };
  confidence_level: number;
  prediction_date: string;
  factors: string[];
}

export interface TransactionAnomaly {
  transaction_id: string;
  type: 'unusual_amount' | 'unusual_merchant' | 'unusual_category' | 'unusual_timing';
  description: string;
  confidence_score: number;
  suggested_actions: string[];
}

export interface FinancialRecommendation {
  id: string;
  type: 'savings_opportunity' | 'budget_adjustment' | 'category_optimization' | 'goal_setting';
  title: string;
  description: string;
  potential_impact: number;
  difficulty: 'easy' | 'moderate' | 'difficult';
  category?: string;
  actions: RecommendationAction[];
}

export interface RecommendationAction {
  description: string;
  priority: 'high' | 'medium' | 'low';
  estimated_time: string;
}

// Webhook Types
export interface WebhookConfiguration {
  id: string;
  name: string;
  description: string;
  url: string;
  events: WebhookEvent[];
  headers: Record<string, string>;
  secret: string;
  active: boolean;
  created_at: string;
  updated_at: string;
  last_triggered_at?: string;
}

export interface WebhookEvent {
  event_type: 'transaction.created' | 'transaction.updated' | 'transaction.deleted' | 
              'account.created' | 'account.updated' | 'account.deleted' |
              'budget.exceeded' | 'goal.achieved' | 'report.generated' |
              'user.login' | 'user.logout' | 'system.maintenance';
  description: string;
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event_type: string;
  status: 'pending' | 'delivered' | 'failed' | 'retrying';
  attempts: number;
  last_attempt_at?: string;
  next_retry_at?: string;
  response_status?: number;
  response_body?: string;
  error_message?: string;
  payload: Record<string, any>;
  created_at: string;
}

// Audit and Compliance Types
export interface AuditEvent {
  id: string;
  event_type: string;
  user_id?: string;
  user_email?: string;
  resource_type: string;
  resource_id?: string;
  action: string;
  details: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  timestamp: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  compliance_flags: ComplianceFlag[];
}

export interface ComplianceFlag {
  framework: 'GDPR' | 'SOX' | 'PCI_DSS' | 'CCPA' | 'HIPAA';
  requirement: string;
  status: 'compliant' | 'non_compliant' | 'warning';
  details: string;
}

export interface AuditReport {
  id: string;
  title: string;
  description: string;
  period: {
    start_date: string;
    end_date: string;
  };
  total_events: number;
  events_by_severity: Record<string, number>;
  compliance_status: ComplianceStatus;
  findings: AuditFinding[];
  recommendations: string[];
  generated_at: string;
  generated_by: string;
}

export interface ComplianceStatus {
  overall_score: number;
  frameworks: Record<string, FrameworkCompliance>;
}

export interface FrameworkCompliance {
  score: number;
  total_requirements: number;
  compliant_requirements: number;
  non_compliant_requirements: number;
  warnings: number;
}

export interface AuditFinding {
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  description: string;
  affected_resources: string[];
  recommendation: string;
  compliance_impact: string[];
}

// Cache Management Types
export interface CacheStatistics {
  total_keys: number;
  memory_usage_mb: number;
  hit_rate: number;
  miss_rate: number;
  evictions: number;
  expired_keys: number;
  average_ttl_seconds: number;
  top_keys: CacheKeyInfo[];
}

export interface CacheKeyInfo {
  key: string;
  size_bytes: number;
  ttl_seconds: number;
  hit_count: number;
  created_at: string;
  last_accessed: string;
}

export interface CacheOperation {
  operation: 'get' | 'set' | 'delete' | 'flush' | 'invalidate';
  key?: string;
  pattern?: string;
  success: boolean;
  execution_time_ms: number;
  timestamp: string;
}

// Migration Types
export interface MigrationStatus {
  total_migrations: number;
  applied_migrations: number;
  pending_migrations: number;
  recent_executions: number;
  last_migration?: string;
  status: 'up_to_date' | 'pending_migrations';
}

export interface Migration {
  id: string;
  version: string;
  name: string;
  description: string;
  migration_type: 'schema' | 'data' | 'index' | 'cleanup' | 'performance' | 'security' | 'feature';
  author: string;
  created_at: string;
  dependencies: string[];
  requires_downtime: boolean;
  estimated_duration_minutes: number;
  dry_run_supported: boolean;
}

export interface MigrationExecution {
  id: string;
  migration_id: string;
  migration_version: string;
  direction: 'up' | 'down';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'rolled_back' | 'skipped';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  steps_completed: number;
  total_steps: number;
  error_message?: string;
  dry_run: boolean;
}

export interface RunMigrationsRequest {
  target_version?: string;
  dry_run: boolean;
  force: boolean;
}

export interface CreateMigrationRequest {
  name: string;
  description: string;
  migration_type: string;
  author: string;
}

// GraphQL Types
export interface GraphQLQuery {
  query: string;
  variables?: Record<string, any>;
  operationName?: string;
}

export interface GraphQLResponse<T = any> {
  data?: T;
  errors?: GraphQLError[];
  extensions?: Record<string, any>;
}

export interface GraphQLError {
  message: string;
  locations?: GraphQLErrorLocation[];
  path?: (string | number)[];
  extensions?: Record<string, any>;
}

export interface GraphQLErrorLocation {
  line: number;
  column: number;
}

// Admin Dashboard Types
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  database: ServiceHealth;
  cache: ServiceHealth;
  external_apis: Record<string, ServiceHealth>;
  performance_metrics: PerformanceMetrics;
  last_checked: string;
}

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  response_time_ms: number;
  error_rate: number;
  uptime_percentage: number;
  last_error?: string;
}

export interface PerformanceMetrics {
  cpu_usage_percent: number;
  memory_usage_percent: number;
  disk_usage_percent: number;
  active_connections: number;
  requests_per_minute: number;
  average_response_time_ms: number;
}