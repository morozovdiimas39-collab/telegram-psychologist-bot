import func2url from '../../backend/func2url.json';

export const API_ENDPOINTS = {
  metrikaGoals: func2url['metrika-goals'],
  quizApi: func2url['quiz-api'],
  migrate: func2url['migrate'],
  deployFunctions: func2url['deploy-functions'],
  updateFunc2url: func2url['update-func2url'],
  ycCreate: func2url['yc-create'],
  ycSetup: func2url['yc-setup'],
  deploy: func2url['deploy'],
  setupWebhook: func2url['setup-webhook'],
};

export type ApiEndpoint = keyof typeof API_ENDPOINTS;