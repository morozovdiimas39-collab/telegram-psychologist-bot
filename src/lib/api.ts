import func2url from '../../backend/func2url.json';
import { MIGRATE_URL } from './migrate-url';
import { SETUP_SSL_URL } from './setup-ssl-url';

export const API_ENDPOINTS = {
  metrikaGoals: func2url['metrika-goals'],
  quizApi: func2url['quiz-api'],
  migrate: MIGRATE_URL,
  setupSsl: SETUP_SSL_URL || (func2url as Record<string, string>)['setup-ssl'] || '',
  deployFunctions: func2url['deploy-functions'],
  ycSync: func2url['yc-sync'],
  deploy: func2url['deploy'],
  deployLong: func2url['deploy-long'],
  deployConfig: func2url['deploy-config'],
  vmSetup: func2url['vm-setup'],
  vmList: func2url['vm-list'],
  vmSshKey: func2url['vm-ssh-key'] || '', // Будет добавлено после деплоя функции
  setupDatabase: func2url['setup-database'] || '', // Будет добавлено после деплоя функции
};

export type ApiEndpoint = keyof typeof API_ENDPOINTS;