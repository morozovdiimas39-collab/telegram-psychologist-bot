import { API_ENDPOINTS } from './api';

const API_URL = API_ENDPOINTS.quizApi;

export interface Answer {
  id: number;
  answer_text: string;
  answer_value: string;
  answer_order: number;
}

export interface Question {
  id: number;
  question_text: string;
  question_order: number;
  metrika_goal_prefix: string;
  answers: Answer[];
}

export interface Quiz {
  id: number;
  title: string;
  slug: string;
  description: string;
  yandex_metrika_id: string | null;
  is_active: boolean;
  questions: Question[];
}

export const quizApi = {
  async getQuiz(slug: string): Promise<Quiz> {
    const response = await fetch(`${API_URL}/?action=get&slug=${slug}`);
    if (!response.ok) {
      throw new Error('Quiz not found');
    }
    return response.json();
  },

  async getAllQuizzes(): Promise<Omit<Quiz, 'questions'>[]> {
    const response = await fetch(`${API_URL}/?action=list`);
    if (!response.ok) {
      throw new Error('Failed to load quizzes');
    }
    return response.json();
  },

  async submitQuiz(data: {
    quiz_id: number;
    answers: { [key: number]: number };
    contactInfo: { name: string; phone: string; email: string };
    segment_key: string;
  }): Promise<{ success: boolean; lead_id: number }> {
    const response = await fetch(`${API_URL}/?action=submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error('Failed to submit quiz');
    }
    return response.json();
  },

  async createMetrikaGoalsAndSegments(quiz: Quiz): Promise<{
    success: boolean;
    created_goals: Array<{ name: string; id?: number; status: string }>;
    created_segments: Array<{ name: string; id?: number; status: string }>;
  }> {
    const response = await fetch(API_ENDPOINTS.metrikaGoals, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ quiz }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create Metrika goals');
    }
    return response.json();
  },
};