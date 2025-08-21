export const environment = {
  production: false,
  apiUrl: 'http://localhost:8080/api/v1',
  googleClientId: '811175185894-gtq53kgq436fup4s2hvpo47prpvum17v.apps.googleusercontent.com', // Placeholder para desarrollo
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