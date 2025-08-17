import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { CanActivateFn } from '@angular/router';

import { authGuard, publicGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('authGuard', () => {
  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let routerSpy: jasmine.SpyObj<Router>;

  const executeGuard: CanActivateFn = (...guardParameters) => 
    TestBed.runInInjectionContext(() => authGuard(...guardParameters));

  const executePublicGuard: CanActivateFn = (...guardParameters) => 
    TestBed.runInInjectionContext(() => publicGuard(...guardParameters));

  beforeEach(() => {
    const authServiceSpyObj = jasmine.createSpyObj('AuthService', ['isAuthenticated']);
    const routerSpyObj = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authServiceSpyObj },
        { provide: Router, useValue: routerSpyObj }
      ]
    });

    authServiceSpy = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  describe('authGuard', () => {
    it('should return true when user is authenticated', () => {
      authServiceSpy.isAuthenticated.and.returnValue(true);

      const result = executeGuard({} as any, {} as any);

      expect(result).toBe(true);
      expect(routerSpy.navigate).not.toHaveBeenCalled();
    });

    it('should redirect to login when user is not authenticated', () => {
      authServiceSpy.isAuthenticated.and.returnValue(false);

      const result = executeGuard({} as any, {} as any);

      expect(result).toBe(false);
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login']);
    });
  });

  describe('publicGuard', () => {
    it('should return true when user is not authenticated', () => {
      authServiceSpy.isAuthenticated.and.returnValue(false);

      const result = executePublicGuard({} as any, {} as any);

      expect(result).toBe(true);
      expect(routerSpy.navigate).not.toHaveBeenCalled();
    });

    it('should redirect to dashboard when user is authenticated', () => {
      authServiceSpy.isAuthenticated.and.returnValue(true);

      const result = executePublicGuard({} as any, {} as any);

      expect(result).toBe(false);
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/dashboard']);
    });
  });
});