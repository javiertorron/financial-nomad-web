export const environment = {
  production: true,
  apiUrl: '/api/v1',
  googleClientId: '811175185894-gtq53kgq436fup4s2hvpo47prpvum17v.apps.googleusercontent.com', // Se configura en build time
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