import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpService } from './http.service';
import {
  Category,
  CategorySummary,
  CategoryType,
  CreateCategoryRequest,
  UpdateCategoryRequest
} from '../types/financial.types';

@Injectable({
  providedIn: 'root'
})
export class CategoryService {
  private readonly baseUrl = '/categories';

  constructor(private httpService: HttpService) {}

  /**
   * Create a new category
   */
  createCategory(request: CreateCategoryRequest): Observable<Category> {
    return this.httpService.post<Category>(this.baseUrl, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get all categories for the current user
   */
  getCategories(
    categoryType?: CategoryType,
    parentId?: string,
    activeOnly: boolean = false
  ): Observable<CategorySummary[]> {
    const params: any = {};
    if (categoryType) params.category_type = categoryType;
    if (parentId) params.parent_id = parentId;
    if (activeOnly) params.active_only = 'true';

    return this.httpService.get<CategorySummary[]>(this.baseUrl, params).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get a specific category by ID
   */
  getCategory(categoryId: string): Observable<Category> {
    return this.httpService.get<Category>(`${this.baseUrl}/${categoryId}`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Update an existing category
   */
  updateCategory(categoryId: string, request: UpdateCategoryRequest): Observable<Category> {
    return this.httpService.put<Category>(`${this.baseUrl}/${categoryId}`, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Delete a category (soft delete)
   */
  deleteCategory(categoryId: string): Observable<void> {
    return this.httpService.delete<void>(`${this.baseUrl}/${categoryId}`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get categories by type
   */
  getCategoriesByType(categoryType: CategoryType, activeOnly: boolean = true): Observable<CategorySummary[]> {
    return this.getCategories(categoryType, undefined, activeOnly);
  }

  /**
   * Get income categories
   */
  getIncomeCategories(activeOnly: boolean = true): Observable<CategorySummary[]> {
    return this.getCategoriesByType(CategoryType.INCOME, activeOnly);
  }

  /**
   * Get expense categories
   */
  getExpenseCategories(activeOnly: boolean = true): Observable<CategorySummary[]> {
    return this.getCategoriesByType(CategoryType.EXPENSE, activeOnly);
  }

  /**
   * Get transfer categories
   */
  getTransferCategories(activeOnly: boolean = true): Observable<CategorySummary[]> {
    return this.getCategoriesByType(CategoryType.TRANSFER, activeOnly);
  }

  /**
   * Get subcategories for a parent category
   */
  getSubcategories(parentId: string, activeOnly: boolean = true): Observable<CategorySummary[]> {
    return this.getCategories(undefined, parentId, activeOnly);
  }

  /**
   * Get root categories (no parent)
   */
  getRootCategories(categoryType?: CategoryType, activeOnly: boolean = true): Observable<CategorySummary[]> {
    // This will need to be filtered on the frontend since the API doesn't have a specific filter for null parent_id
    return this.getCategories(categoryType, undefined, activeOnly);
  }

  /**
   * Get category type display name
   */
  getCategoryTypeDisplayName(categoryType: CategoryType): string {
    const typeMap: Record<CategoryType, string> = {
      [CategoryType.INCOME]: 'Ingreso',
      [CategoryType.EXPENSE]: 'Gasto',
      [CategoryType.TRANSFER]: 'Transferencia'
    };
    return typeMap[categoryType] || categoryType;
  }

  /**
   * Format monthly budget for display
   */
  formatMonthlyBudget(budget: string | undefined, currency: string = 'EUR'): string | null {
    if (!budget) return null;
    const amount = parseFloat(budget);
    if (isNaN(amount)) return null;
    
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Get monthly budget as number
   */
  getMonthlyBudgetAmount(category: Category | CategorySummary): number {
    if (!category.monthly_budget) return 0;
    return parseFloat(category.monthly_budget) || 0;
  }

  /**
   * Check if category is a system category
   */
  isSystemCategory(category: Category | CategorySummary): boolean {
    return category.is_system === true;
  }

  /**
   * Filter categories by active status
   */
  getActiveCategories(categories: (Category | CategorySummary)[]): (Category | CategorySummary)[] {
    return categories.filter(category => category.is_active);
  }

  /**
   * Filter categories by type
   */
  filterCategoriesByType(categories: (Category | CategorySummary)[], categoryType: CategoryType): (Category | CategorySummary)[] {
    return categories.filter(category => category.category_type === categoryType);
  }

  /**
   * Get root categories from a list (categories without parent)
   */
  getRootCategoriesFromList(categories: CategorySummary[]): CategorySummary[] {
    return categories.filter(category => !category.parent_name);
  }

  /**
   * Build category hierarchy (for display purposes)
   */
  buildCategoryHierarchy(categories: CategorySummary[]): CategorySummary[] {
    // This is a simplified version - in a real app you might want to build a proper tree structure
    const rootCategories = this.getRootCategoriesFromList(categories);
    const subcategories = categories.filter(category => category.parent_name);
    
    // Sort root categories first, then subcategories
    return [...rootCategories.sort((a, b) => a.name.localeCompare(b.name)),
            ...subcategories.sort((a, b) => a.name.localeCompare(b.name))];
  }
}