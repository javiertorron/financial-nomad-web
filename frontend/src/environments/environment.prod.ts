export const environment = {
  production: true,
  apiUrl: '/api/v1',
  googleClientId: '783748328773-l80u4vhcmh90oa5d1fhf0mfhrvhppfhe.apps.googleusercontent.com', // Se configura en build time
  firebaseConfig: {
    projectId: 'financial-nomad-prod',
    useEmulator: false,
    emulatorHost: '',
    emulatorPort: 0
  },
  features: {
    enableAsanaIntegration: true,
    enableExportFeatures: true,
    enablePwaFeatures: true,
    enableOfflineMode: true
  },
  logging: {
    level: 'ERROR',
    enableConsoleLogging: false
  }
};