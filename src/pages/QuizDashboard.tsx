import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Icon from '@/components/ui/icon';
import { toast } from 'sonner';
import { quizApi } from '@/lib/quizApi';

interface Quiz {
  id: number;
  title: string;
  slug: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

export default function QuizDashboard() {
  const navigate = useNavigate();
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadQuizzes();
  }, []);

  const loadQuizzes = async () => {
    try {
      const data = await quizApi.getAllQuizzes();
      setQuizzes(data);
      setIsLoading(false);
    } catch (error) {
      toast.error('Ошибка загрузки квизов');
      console.error(error);
      setIsLoading(false);
    }
  };

  const copyLink = (slug: string) => {
    const url = `${window.location.origin}/quiz/${slug}`;
    navigator.clipboard.writeText(url);
    toast.success('Ссылка скопирована!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-6xl py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
              <span className="text-5xl">📊</span>
              Мои квизы
            </h1>
            <p className="text-slate-400">
              Создавай квизы с автоматической сегментацией и интеграцией с Метрикой
            </p>
          </div>
          <Button
            onClick={() => navigate('/quiz-builder')}
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          >
            <Icon name="Plus" size={20} className="mr-2" />
            Создать квиз
          </Button>
        </div>

        {/* Stats */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400 mb-1">Всего квизов</p>
                  <p className="text-3xl font-bold text-white">{quizzes.length}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <Icon name="FileText" size={24} className="text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400 mb-1">Активных</p>
                  <p className="text-3xl font-bold text-white">
                    {quizzes.filter(q => q.is_active).length}
                  </p>
                </div>
                <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                  <Icon name="CheckCircle" size={24} className="text-green-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400 mb-1">Лидов сегодня</p>
                  <p className="text-3xl font-bold text-white">0</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <Icon name="Users" size={24} className="text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quizzes List */}
        {isLoading ? (
          <div className="text-center text-white py-12">Загрузка...</div>
        ) : quizzes.length === 0 ? (
          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-12 text-center">
              <div className="text-6xl mb-4">📋</div>
              <h3 className="text-xl font-bold text-white mb-2">Квизов пока нет</h3>
              <p className="text-slate-400 mb-6">
                Создай первый квиз и начни собирать лиды с умной сегментацией
              </p>
              <Button
                onClick={() => navigate('/quiz-builder')}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              >
                <Icon name="Plus" size={20} className="mr-2" />
                Создать квиз
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {quizzes.map((quiz) => (
              <Card key={quiz.id} className="bg-white/5 backdrop-blur border-white/10 hover:bg-white/10 transition-all">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <CardTitle className="text-white text-xl">{quiz.title}</CardTitle>
                        {quiz.is_active ? (
                          <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                            Активен
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">
                            Неактивен
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-400 mb-3">{quiz.description}</p>
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Icon name="Link" size={14} />
                        <code className="text-xs">/quiz/{quiz.slug}</code>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/quiz/${quiz.slug}`)}
                        className="border-white/20 text-white hover:bg-white/10"
                      >
                        <Icon name="Eye" size={16} className="mr-2" />
                        Открыть
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyLink(quiz.slug)}
                        className="border-white/20 text-white hover:bg-white/10"
                      >
                        <Icon name="Copy" size={16} />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/quiz-builder?id=${quiz.id}`)}
                        className="border-white/20 text-white hover:bg-white/10"
                      >
                        <Icon name="Edit" size={16} />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <p className="text-2xl font-bold text-white">0</p>
                      <p className="text-xs text-slate-400">Просмотров</p>
                    </div>
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <p className="text-2xl font-bold text-white">0</p>
                      <p className="text-xs text-slate-400">Завершений</p>
                    </div>
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <p className="text-2xl font-bold text-white">0%</p>
                      <p className="text-xs text-slate-400">Конверсия</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Quick Guide */}
        <Card className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 backdrop-blur border-blue-500/20 mt-8">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <Icon name="Lightbulb" size={24} className="text-blue-400" />
              </div>
              <div>
                <h3 className="text-white font-bold mb-2">Как это работает?</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Создаешь квиз с вопросами и вариантами ответов</li>
                  <li>• Указываешь ID Яндекс.Метрики - цели создаются автоматически</li>
                  <li>• Каждый выбор пользователя = отдельная цель в Метрике</li>
                  <li>• Формируется уникальный сегмент (например: 1к_наличка_год)</li>
                  <li>• Запускаешь РК в Директе под каждый сегмент = дешевые лиды!</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}