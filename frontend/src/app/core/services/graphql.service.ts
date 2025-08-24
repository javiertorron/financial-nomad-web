import { Injectable } from '@angular/core';
import { Apollo, gql } from 'apollo-angular';
import { HttpLink } from 'apollo-angular/http';
import { InMemoryCache } from '@apollo/client/core';
import { setContext } from '@apollo/client/link/context';
import { onError } from '@apollo/client/link/error';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, catchError } from 'rxjs/operators';

import { ConfigService } from './config.service';
import { AuthService } from './auth.service';
import { NotificationService } from './notification.service';
import {
  GraphQLQuery,
  GraphQLResponse,
  GraphQLError
} from '../types/enterprise.types';

export interface QueryOptions {
  variables?: any;
  fetchPolicy?: 'cache-first' | 'cache-and-network' | 'network-only' | 'cache-only' | 'standby';
  errorPolicy?: 'none' | 'ignore' | 'all';
  pollInterval?: number;
}

export interface MutationOptions {
  variables?: any;
  errorPolicy?: 'none' | 'ignore' | 'all';
  optimisticResponse?: any;
  update?: (cache: any, result: any) => void;
}

export interface SubscriptionOptions {
  variables?: any;
  errorPolicy?: 'none' | 'ignore' | 'all';
}

@Injectable({
  providedIn: 'root'
})
export class GraphQLService {
  private readonly graphqlUrl = `${this.config.apiUrl}/api/v1/graphql`;
  private isConnected = new BehaviorSubject<boolean>(false);
  public connected$ = this.isConnected.asObservable();

  // Common GraphQL fragments
  public readonly FRAGMENTS = {
    TRANSACTION_BASIC: gql`
      fragment TransactionBasic on Transaction {
        id
        amount
        description
        date
        category_id
        account_id
        transaction_type
        created_at
        updated_at
      }
    `,
    
    ACCOUNT_BASIC: gql`
      fragment AccountBasic on Account {
        id
        name
        account_type
        balance
        currency
        is_active
        created_at
        updated_at
      }
    `,

    CATEGORY_BASIC: gql`
      fragment CategoryBasic on Category {
        id
        name
        category_type
        parent_id
        color
        icon
        created_at
        updated_at
      }
    `,

    BUDGET_BASIC: gql`
      fragment BudgetBasic on Budget {
        id
        name
        amount
        category_id
        period_type
        start_date
        end_date
        created_at
        updated_at
      }
    `,

    USER_BASIC: gql`
      fragment UserBasic on User {
        id
        email
        full_name
        preferences
        created_at
        updated_at
      }
    `
  };

  // Common queries
  public readonly QUERIES = {
    GET_TRANSACTIONS: gql`
      ${this.FRAGMENTS.TRANSACTION_BASIC}
      query GetTransactions(
        $filters: TransactionFilterInput
        $pagination: PaginationInput
        $sorting: SortingInput
      ) {
        transactions(filters: $filters, pagination: $pagination, sorting: $sorting) {
          items {
            ...TransactionBasic
            category {
              name
              color
            }
            account {
              name
            }
          }
          totalCount
          hasNextPage
          hasPreviousPage
        }
      }
    `,

    GET_ACCOUNTS: gql`
      ${this.FRAGMENTS.ACCOUNT_BASIC}
      query GetAccounts($filters: AccountFilterInput) {
        accounts(filters: $filters) {
          ...AccountBasic
          transactions_count
          last_transaction_date
        }
      }
    `,

    GET_CATEGORIES: gql`
      ${this.FRAGMENTS.CATEGORY_BASIC}
      query GetCategories($type: CategoryType) {
        categories(type: $type) {
          ...CategoryBasic
          parent {
            name
          }
          children {
            ...CategoryBasic
          }
          transactions_count
          total_amount
        }
      }
    `,

    GET_BUDGETS: gql`
      ${this.FRAGMENTS.BUDGET_BASIC}
      query GetBudgets($period: PeriodType) {
        budgets(period: $period) {
          ...BudgetBasic
          category {
            name
            color
          }
          spent_amount
          remaining_amount
          utilization_percentage
          status
        }
      }
    `,

    GET_DASHBOARD_DATA: gql`
      query GetDashboardData($dateRange: DateRangeInput) {
        dashboard(dateRange: $dateRange) {
          totalBalance
          totalIncome
          totalExpenses
          netWorth
          recentTransactions {
            ...TransactionBasic
            category { name color }
            account { name }
          }
          topCategories {
            category_id
            category_name
            amount
            transaction_count
          }
          monthlyTrends {
            month
            income
            expenses
            net
          }
        }
      }
      ${this.FRAGMENTS.TRANSACTION_BASIC}
    `,

    SEARCH_GLOBAL: gql`
      query SearchGlobal($query: String!, $types: [SearchType!]) {
        search(query: $query, types: $types) {
          transactions {
            ...TransactionBasic
            category { name color }
            account { name }
          }
          accounts {
            ...AccountBasic
          }
          categories {
            ...CategoryBasic
          }
        }
      }
      ${this.FRAGMENTS.TRANSACTION_BASIC}
      ${this.FRAGMENTS.ACCOUNT_BASIC}
      ${this.FRAGMENTS.CATEGORY_BASIC}
    `
  };

  // Common mutations
  public readonly MUTATIONS = {
    CREATE_TRANSACTION: gql`
      ${this.FRAGMENTS.TRANSACTION_BASIC}
      mutation CreateTransaction($input: CreateTransactionInput!) {
        createTransaction(input: $input) {
          ...TransactionBasic
          category { name color }
          account { name }
        }
      }
    `,

    UPDATE_TRANSACTION: gql`
      ${this.FRAGMENTS.TRANSACTION_BASIC}
      mutation UpdateTransaction($id: ID!, $input: UpdateTransactionInput!) {
        updateTransaction(id: $id, input: $input) {
          ...TransactionBasic
          category { name color }
          account { name }
        }
      }
    `,

    DELETE_TRANSACTION: gql`
      mutation DeleteTransaction($id: ID!) {
        deleteTransaction(id: $id) {
          success
          message
        }
      }
    `,

    CREATE_ACCOUNT: gql`
      ${this.FRAGMENTS.ACCOUNT_BASIC}
      mutation CreateAccount($input: CreateAccountInput!) {
        createAccount(input: $input) {
          ...AccountBasic
        }
      }
    `,

    UPDATE_ACCOUNT: gql`
      ${this.FRAGMENTS.ACCOUNT_BASIC}
      mutation UpdateAccount($id: ID!, $input: UpdateAccountInput!) {
        updateAccount(id: $id, input: $input) {
          ...AccountBasic
        }
      }
    `,

    CREATE_BUDGET: gql`
      ${this.FRAGMENTS.BUDGET_BASIC}
      mutation CreateBudget($input: CreateBudgetInput!) {
        createBudget(input: $input) {
          ...BudgetBasic
          category { name color }
        }
      }
    `,

    BULK_CREATE_TRANSACTIONS: gql`
      mutation BulkCreateTransactions($transactions: [CreateTransactionInput!]!) {
        bulkCreateTransactions(transactions: $transactions) {
          success
          created_count
          failed_count
          errors {
            index
            message
          }
        }
      }
    `
  };

  // Subscriptions
  public readonly SUBSCRIPTIONS = {
    TRANSACTION_CREATED: gql`
      ${this.FRAGMENTS.TRANSACTION_BASIC}
      subscription OnTransactionCreated($userId: ID!) {
        transactionCreated(userId: $userId) {
          ...TransactionBasic
          category { name color }
          account { name }
        }
      }
    `,

    ACCOUNT_BALANCE_UPDATED: gql`
      subscription OnAccountBalanceUpdated($userId: ID!, $accountId: ID) {
        accountBalanceUpdated(userId: $userId, accountId: $accountId) {
          account_id
          old_balance
          new_balance
          timestamp
        }
      }
    `,

    BUDGET_ALERT: gql`
      subscription OnBudgetAlert($userId: ID!) {
        budgetAlert(userId: $userId) {
          budget_id
          category_name
          threshold_percentage
          current_percentage
          alert_type
          timestamp
        }
      }
    `
  };

  constructor(
    private apollo: Apollo,
    private httpLink: HttpLink,
    private config: ConfigService,
    private auth: AuthService,
    private notification: NotificationService
  ) {
    this.initializeApollo();
  }

  private initializeApollo(): void {
    // Authentication link
    const authLink = setContext((_, { headers }) => {
      const token = this.auth.getToken();
      return {
        headers: {
          ...headers,
          authorization: token ? `Bearer ${token}` : '',
        }
      };
    });

    // Error handling link
    const errorLink = onError(({ graphQLErrors, networkError, operation, forward }) => {
      if (graphQLErrors) {
        graphQLErrors.forEach(({ message, locations, path }) => {
          console.error(`GraphQL error: Message: ${message}, Location: ${locations}, Path: ${path}`);
          this.notification.showError(`GraphQL Error: ${message}`);
        });
      }

      if (networkError) {
        console.error(`Network error: ${networkError}`);
        this.notification.showError('Network error occurred');
        this.isConnected.next(false);
      }
    });

    // Create HTTP link
    const httpLinkInstance = this.httpLink.create({
      uri: this.graphqlUrl
    });

    // Create Apollo client
    this.apollo.create({
      link: authLink.concat(errorLink).concat(httpLinkInstance),
      cache: new InMemoryCache({
        typePolicies: {
          Transaction: {
            fields: {
              category: {
                merge: true
              },
              account: {
                merge: true
              }
            }
          },
          Account: {
            fields: {
              transactions: {
                merge: false
              }
            }
          },
          Query: {
            fields: {
              transactions: {
                keyArgs: ['filters'],
                merge(existing = { items: [], totalCount: 0 }, incoming) {
                  return {
                    ...incoming,
                    items: [...existing.items, ...incoming.items]
                  };
                }
              }
            }
          }
        }
      }),
      defaultOptions: {
        watchQuery: {
          errorPolicy: 'all',
          fetchPolicy: 'cache-and-network'
        },
        query: {
          errorPolicy: 'all',
          fetchPolicy: 'cache-first'
        },
        mutate: {
          errorPolicy: 'all'
        }
      }
    });

    this.isConnected.next(true);
  }

  // Query methods
  query<T = any>(query: any, options?: QueryOptions): Observable<T> {
    return this.apollo.query<T>({
      query,
      variables: options?.variables,
      fetchPolicy: options?.fetchPolicy || 'cache-first',
      errorPolicy: options?.errorPolicy || 'all'
    }).pipe(
      map(result => result.data),
      catchError(error => {
        console.error('GraphQL Query Error:', error);
        throw error;
      })
    );
  }

  watchQuery<T = any>(query: any, options?: QueryOptions): Observable<T> {
    return this.apollo.watchQuery<T>({
      query,
      variables: options?.variables,
      fetchPolicy: options?.fetchPolicy || 'cache-and-network',
      errorPolicy: options?.errorPolicy || 'all',
      pollInterval: options?.pollInterval
    }).valueChanges.pipe(
      map(result => result.data),
      catchError(error => {
        console.error('GraphQL WatchQuery Error:', error);
        throw error;
      })
    );
  }

  // Mutation methods
  mutate<T = any>(mutation: any, options?: MutationOptions): Observable<T> {
    return this.apollo.mutate<T>({
      mutation,
      variables: options?.variables,
      errorPolicy: options?.errorPolicy || 'all',
      optimisticResponse: options?.optimisticResponse,
      update: options?.update
    }).pipe(
      map(result => result.data!),
      catchError(error => {
        console.error('GraphQL Mutation Error:', error);
        throw error;
      })
    );
  }

  // Subscription methods
  subscribe<T = any>(subscription: any, options?: SubscriptionOptions): Observable<T> {
    return this.apollo.subscribe<T>({
      query: subscription,
      variables: options?.variables,
      errorPolicy: options?.errorPolicy || 'all'
    }).pipe(
      map(result => result.data!),
      catchError(error => {
        console.error('GraphQL Subscription Error:', error);
        throw error;
      })
    );
  }

  // Convenience methods for common operations
  getTransactions(filters?: any, pagination?: any, sorting?: any): Observable<any> {
    return this.query(this.QUERIES.GET_TRANSACTIONS, {
      variables: { filters, pagination, sorting }
    });
  }

  watchTransactions(filters?: any, pagination?: any, sorting?: any): Observable<any> {
    return this.watchQuery(this.QUERIES.GET_TRANSACTIONS, {
      variables: { filters, pagination, sorting }
    });
  }

  getAccounts(filters?: any): Observable<any> {
    return this.query(this.QUERIES.GET_ACCOUNTS, {
      variables: { filters }
    });
  }

  getCategories(type?: string): Observable<any> {
    return this.query(this.QUERIES.GET_CATEGORIES, {
      variables: { type }
    });
  }

  getBudgets(period?: string): Observable<any> {
    return this.query(this.QUERIES.GET_BUDGETS, {
      variables: { period }
    });
  }

  getDashboardData(dateRange?: any): Observable<any> {
    return this.query(this.QUERIES.GET_DASHBOARD_DATA, {
      variables: { dateRange }
    });
  }

  searchGlobal(query: string, types?: string[]): Observable<any> {
    return this.query(this.QUERIES.SEARCH_GLOBAL, {
      variables: { query, types }
    });
  }

  createTransaction(input: any): Observable<any> {
    return this.mutate(this.MUTATIONS.CREATE_TRANSACTION, {
      variables: { input }
    });
  }

  updateTransaction(id: string, input: any): Observable<any> {
    return this.mutate(this.MUTATIONS.UPDATE_TRANSACTION, {
      variables: { id, input }
    });
  }

  deleteTransaction(id: string): Observable<any> {
    return this.mutate(this.MUTATIONS.DELETE_TRANSACTION, {
      variables: { id }
    });
  }

  // Subscription helpers
  subscribeToTransactionUpdates(userId: string): Observable<any> {
    return this.subscribe(this.SUBSCRIPTIONS.TRANSACTION_CREATED, {
      variables: { userId }
    });
  }

  subscribeToAccountBalanceUpdates(userId: string, accountId?: string): Observable<any> {
    return this.subscribe(this.SUBSCRIPTIONS.ACCOUNT_BALANCE_UPDATED, {
      variables: { userId, accountId }
    });
  }

  subscribeToBudgetAlerts(userId: string): Observable<any> {
    return this.subscribe(this.SUBSCRIPTIONS.BUDGET_ALERT, {
      variables: { userId }
    });
  }

  // Cache management
  clearCache(): void {
    this.apollo.client.clearStore();
  }

  refetchQueries(queryNames: string[]): void {
    this.apollo.client.refetchQueries({
      include: queryNames
    });
  }

  // Advanced features
  createCustomQuery(queryString: string, variables?: any): Observable<any> {
    const customQuery = gql`${queryString}`;
    return this.query(customQuery, { variables });
  }

  createCustomMutation(mutationString: string, variables?: any): Observable<any> {
    const customMutation = gql`${mutationString}`;
    return this.mutate(customMutation, { variables });
  }

  // Batch operations
  batchQueries(queries: { query: any; variables?: any }[]): Observable<any[]> {
    const batchedQueries = queries.map(({ query, variables }) => 
      this.query(query, { variables }).toPromise()
    );
    
    return new Observable(observer => {
      Promise.all(batchedQueries)
        .then(results => {
          observer.next(results);
          observer.complete();
        })
        .catch(error => observer.error(error));
    });
  }

  // Performance monitoring
  getQueryPerformance(): any {
    // Access Apollo DevTools data if available
    return this.apollo.client.cache.extract();
  }

  // Connection status
  checkConnection(): Observable<boolean> {
    const healthCheck = gql`
      query HealthCheck {
        health {
          status
          timestamp
        }
      }
    `;

    return this.query(healthCheck).pipe(
      map(() => {
        this.isConnected.next(true);
        return true;
      }),
      catchError(() => {
        this.isConnected.next(false);
        return [false];
      })
    );
  }
}