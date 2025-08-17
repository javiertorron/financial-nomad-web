export const environment = {
  production: false,
  apiUrl: 'http://localhost:8080/api/v1',
  googleClientId: '783748328773-l80u4vhcmh90oa5d1fhf0mfhrvhppfhe.apps.googleusercontent.com', // Placeholder para desarrollo
  firebaseConfig: {
    projectId: 'financial-nomad-dev',
    useEmulator: true,
    emulatorHost: 'localhost',
    emulatorPort: 8081
  },
  features: {
    enableAsanaIntegration: false,
    enableExportFeatures: true,
    enablePwaFeatures: true,
    enableOfflineMode: false
  },
  logging: {
    level: 'DEBUG',
    enableConsoleLogging: true
  }
};