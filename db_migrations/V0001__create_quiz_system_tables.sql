-- Таблица квизов
CREATE TABLE IF NOT EXISTS quizzes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    yandex_metrika_id VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица вопросов
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id),
    question_text TEXT NOT NULL,
    question_order INTEGER NOT NULL,
    metrika_goal_prefix VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица вариантов ответов
CREATE TABLE IF NOT EXISTS answers (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    answer_text VARCHAR(255) NOT NULL,
    answer_value VARCHAR(100) NOT NULL,
    answer_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица лидов
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id),
    name VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    segment_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица ответов на квиз
CREATE TABLE IF NOT EXISTS quiz_responses (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    question_id INTEGER REFERENCES questions(id),
    answer_id INTEGER REFERENCES answers(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_questions_quiz_id ON questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_answers_question_id ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_leads_quiz_id ON leads(quiz_id);
CREATE INDEX IF NOT EXISTS idx_leads_segment_key ON leads(segment_key);
CREATE INDEX IF NOT EXISTS idx_quiz_responses_lead_id ON quiz_responses(lead_id);

-- Вставляем тестовый квиз для недвижимости
INSERT INTO quizzes (title, slug, description, is_active) 
VALUES ('Подбор квартиры', 'realty-quiz', 'Квиз для подбора квартиры с сегментацией по параметрам', true);

-- Вопросы для тестового квиза
INSERT INTO questions (quiz_id, question_text, question_order, metrika_goal_prefix)
VALUES 
    (1, 'Сколько комнат вам нужно?', 1, 'rooms'),
    (1, 'Как планируете оплачивать?', 2, 'payment'),
    (1, 'Когда планируете покупать?', 3, 'timing');

-- Ответы для вопроса "Сколько комнат"
INSERT INTO answers (question_id, answer_text, answer_value, answer_order)
VALUES 
    (1, '1 комната', '1k', 1),
    (1, '2 комнаты', '2k', 2),
    (1, '3 комнаты', '3k', 3);

-- Ответы для вопроса "Оплата"
INSERT INTO answers (question_id, answer_text, answer_value, answer_order)
VALUES 
    (2, 'Рассрочка', 'rassrochka', 1),
    (2, 'Ипотека', 'ipoteka', 2),
    (2, 'Наличные', 'nalichka', 3);

-- Ответы для вопроса "Срок"
INSERT INTO answers (question_id, answer_text, answer_value, answer_order)
VALUES 
    (3, 'В ближайшее время', 'now', 1),
    (3, 'Через полгода', '6months', 2),
    (3, 'Через год', '1year', 3);