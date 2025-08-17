import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { HttpService } from './http.service';

describe('AuthService', () => {
  let service: AuthService;
  let routerSpy: jasmine.SpyObj<Router>;
  let httpServiceSpy: jasmine.SpyObj<HttpService>;

  beforeEach(() => {
    const routerSpyObj = jasmine.createSpyObj('Router', ['navigate']);
    const httpServiceSpyObj = jasmine.createSpyObj('HttpService', ['post', 'get']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: Router, useValue: routerSpyObj },
        { provide: HttpService, useValue: httpServiceSpyObj }
      ]
    });

    service = TestBed.inject(AuthService);
    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    httpServiceSpy = TestBed.inject(HttpService) as jasmine.SpyObj<HttpService>;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should initialize with no authenticated user', () => {
    expect(service.isAuthenticated()).toBeFalse();
    expect(service.user()).toBeNull();
  });

  it('should clear storage and navigate to login on logout', () => {
    spyOn(localStorage, 'removeItem');
    
    service.logout();
    
    expect(localStorage.removeItem).toHaveBeenCalledWith('financial_nomad_token');
    expect(localStorage.removeItem).toHaveBeenCalledWith('financial_nomad_user');
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login']);
    expect(service.user()).toBeNull();
  });

  it('should return null for expired token', () => {
    const expiredTokenInfo = {
      access_token: 'expired-token',
      expires_at: Date.now() - 1000, // Expired 1 second ago
      user: { id: '1', email: 'test@test.com', name: 'Test User' }
    };
    
    spyOn(localStorage, 'getItem').and.returnValue(JSON.stringify(expiredTokenInfo));
    spyOn(localStorage, 'removeItem');
    
    const token = service.getStoredToken();
    
    expect(token).toBeNull();
    expect(localStorage.removeItem).toHaveBeenCalled();
  });

  it('should return valid token when not expired', () => {
    const validTokenInfo = {
      access_token: 'valid-token',
      expires_at: Date.now() + 3600000, // Expires in 1 hour
      user: { id: '1', email: 'test@test.com', name: 'Test User' }
    };
    
    spyOn(localStorage, 'getItem').and.returnValue(JSON.stringify(validTokenInfo));
    
    const token = service.getStoredToken();
    
    expect(token).toBe('valid-token');
  });
});