import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import Icon from '@/components/ui/icon';
import { toast } from 'sonner';

interface Answer {
  id?: number;
  answer_text: string;
  answer_value: string;
  answer_order: number;
}

interface Question {
  id?: number;
  question_text: string;
  question_order: number;
  metrika_goal_prefix: string;
  answers: Answer[];
}

interface Quiz {
  id?: number;
  title: string;
  slug: string;
  description: string;
  yandex_metrika_id: string;
  questions: Question[];
}

export default function QuizBuilder() {
  const [quiz, setQuiz] = useState<Quiz>({
    title: '',
    slug: '',
    description: '',
    yandex_metrika_id: '',
    questions: []
  });

  const addQuestion = () => {
    setQuiz({
      ...quiz,
      questions: [
        ...quiz.questions,
        {
          question_text: '',
          question_order: quiz.questions.length + 1,
          metrika_goal_prefix: '',
          answers: []
        }
      ]
    });
  };

  const updateQuestion = (index: number, field: keyof Question, value: any) => {
    const updated = [...quiz.questions];
    updated[index] = { ...updated[index], [field]: value };
    setQuiz({ ...quiz, questions: updated });
  };

  const deleteQuestion = (index: number) => {
    const updated = quiz.questions.filter((_, i) => i !== index);
    setQuiz({ ...quiz, questions: updated });
  };

  const addAnswer = (questionIndex: number) => {
    const updated = [...quiz.questions];
    updated[questionIndex].answers.push({
      answer_text: '',
      answer_value: '',
      answer_order: updated[questionIndex].answers.length + 1
    });
    setQuiz({ ...quiz, questions: updated });
  };

  const updateAnswer = (questionIndex: number, answerIndex: number, field: keyof Answer, value: any) => {
    const updated = [...quiz.questions];
    updated[questionIndex].answers[answerIndex] = {
      ...updated[questionIndex].answers[answerIndex],
      [field]: value
    };
    setQuiz({ ...quiz, questions: updated });
  };

  const deleteAnswer = (questionIndex: number, answerIndex: number) => {
    const updated = [...quiz.questions];
    updated[questionIndex].answers = updated[questionIndex].answers.filter((_, i) => i !== answerIndex);
    setQuiz({ ...quiz, questions: updated });
  };

  const generateSlug = (title: string) => {
    return title
      .toLowerCase()
      .replace(/[а-я]/g, (char) => {
        const map: { [key: string]: string } = {
          'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
          'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
          'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
          'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
          'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        };
        return map[char] || char;
      })
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  };

  const saveQuiz = async () => {
    if (!quiz.title || !quiz.slug || quiz.questions.length === 0) {
      toast.error('Заполните название, slug и добавьте хотя бы один вопрос');
      return;
    }

    try {
      // TODO: Backend для сохранения квиза
      toast.success('Квиз сохранен!');
      console.log('Quiz data:', quiz);
    } catch (error) {
      toast.error('Ошибка сохранения квиза');
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-6xl py-8">
        <div className="mb-6">
          <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
            <span className="text-5xl">📋</span>
            Конструктор квизов
          </h1>
          <p className="text-slate-400">
            Создавай квизы с автоматической сегментацией для Яндекс.Метрики и Директа
          </p>
        </div>

        {/* Основные настройки квиза */}
        <Card className="bg-white/5 backdrop-blur border-white/10 mb-6">
          <CardHeader>
            <CardTitle className="text-white">Основные настройки</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm text-slate-300 mb-2 block">Название квиза</label>
              <Input
                value={quiz.title}
                onChange={(e) => {
                  setQuiz({ ...quiz, title: e.target.value });
                  if (!quiz.slug) {
                    setQuiz({ ...quiz, title: e.target.value, slug: generateSlug(e.target.value) });
                  }
                }}
                placeholder="Подбор квартиры"
                className="bg-white/10 border-white/20 text-white"
              />
            </div>
            <div>
              <label className="text-sm text-slate-300 mb-2 block">Slug (для URL)</label>
              <Input
                value={quiz.slug}
                onChange={(e) => setQuiz({ ...quiz, slug: e.target.value })}
                placeholder="realty-quiz"
                className="bg-white/10 border-white/20 text-white font-mono"
              />
              <p className="text-xs text-slate-500 mt-1">
                Ссылка: {window.location.origin}/quiz/{quiz.slug || 'slug'}
              </p>
            </div>
            <div>
              <label className="text-sm text-slate-300 mb-2 block">Описание</label>
              <Textarea
                value={quiz.description}
                onChange={(e) => setQuiz({ ...quiz, description: e.target.value })}
                placeholder="Краткое описание квиза"
                className="bg-white/10 border-white/20 text-white"
                rows={2}
              />
            </div>
            <div>
              <label className="text-sm text-slate-300 mb-2 block">ID Яндекс.Метрики</label>
              <Input
                value={quiz.yandex_metrika_id}
                onChange={(e) => setQuiz({ ...quiz, yandex_metrika_id: e.target.value })}
                placeholder="12345678"
                className="bg-white/10 border-white/20 text-white"
              />
            </div>
          </CardContent>
        </Card>

        {/* Вопросы */}
        <div className="space-y-4 mb-6">
          {quiz.questions.map((question, qIndex) => (
            <Card key={qIndex} className="bg-white/5 backdrop-blur border-white/10">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-white text-lg">Вопрос {qIndex + 1}</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteQuestion(qIndex)}
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                >
                  <Icon name="Trash2" size={16} />
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm text-slate-300 mb-2 block">Текст вопроса</label>
                  <Input
                    value={question.question_text}
                    onChange={(e) => updateQuestion(qIndex, 'question_text', e.target.value)}
                    placeholder="Сколько комнат вам нужно?"
                    className="bg-white/10 border-white/20 text-white"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-300 mb-2 block">
                    Префикс цели в Метрике
                  </label>
                  <Input
                    value={question.metrika_goal_prefix}
                    onChange={(e) => updateQuestion(qIndex, 'metrika_goal_prefix', e.target.value)}
                    placeholder="rooms"
                    className="bg-white/10 border-white/20 text-white font-mono"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Пример цели: {question.metrika_goal_prefix || 'prefix'}_1k
                  </p>
                </div>

                {/* Варианты ответов */}
                <div className="space-y-3">
                  <label className="text-sm text-slate-300 block">Варианты ответов</label>
                  {question.answers.map((answer, aIndex) => (
                    <div key={aIndex} className="flex gap-2">
                      <Input
                        value={answer.answer_text}
                        onChange={(e) => updateAnswer(qIndex, aIndex, 'answer_text', e.target.value)}
                        placeholder="1 комната"
                        className="bg-white/10 border-white/20 text-white flex-1"
                      />
                      <Input
                        value={answer.answer_value}
                        onChange={(e) => updateAnswer(qIndex, aIndex, 'answer_value', e.target.value)}
                        placeholder="1k"
                        className="bg-white/10 border-white/20 text-white font-mono w-32"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteAnswer(qIndex, aIndex)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      >
                        <Icon name="X" size={16} />
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => addAnswer(qIndex)}
                    className="border-white/20 text-white hover:bg-white/10"
                  >
                    <Icon name="Plus" size={16} className="mr-2" />
                    Добавить ответ
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Действия */}
        <div className="flex gap-4">
          <Button
            onClick={addQuestion}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Icon name="Plus" size={18} className="mr-2" />
            Добавить вопрос
          </Button>
          <Button
            onClick={saveQuiz}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Icon name="Save" size={18} className="mr-2" />
            Сохранить квиз
          </Button>
        </div>
      </div>
    </div>
  );
}
