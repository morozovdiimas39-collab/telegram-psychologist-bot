import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Icon from '@/components/ui/icon';
import { toast } from 'sonner';

interface Answer {
  id: number;
  answer_text: string;
  answer_value: string;
}

interface Question {
  id: number;
  question_text: string;
  metrika_goal_prefix: string;
  answers: Answer[];
}

interface Quiz {
  id: number;
  title: string;
  description: string;
  yandex_metrika_id: string;
  questions: Question[];
}

export default function QuizPublic() {
  const { slug } = useParams<{ slug: string }>();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<{ [key: number]: number }>({});
  const [contactInfo, setContactInfo] = useState({ name: '', phone: '', email: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    loadQuiz();
  }, [slug]);

  const loadQuiz = async () => {
    try {
      // TODO: Загрузка из backend
      // Временно - тестовые данные
      setQuiz({
        id: 1,
        title: 'Подбор квартиры',
        description: 'Ответьте на несколько вопросов и получите подборку квартир',
        yandex_metrika_id: '12345678',
        questions: [
          {
            id: 1,
            question_text: 'Сколько комнат вам нужно?',
            metrika_goal_prefix: 'rooms',
            answers: [
              { id: 1, answer_text: '1 комната', answer_value: '1k' },
              { id: 2, answer_text: '2 комнаты', answer_value: '2k' },
              { id: 3, answer_text: '3 комнаты', answer_value: '3k' }
            ]
          },
          {
            id: 2,
            question_text: 'Как планируете оплачивать?',
            metrika_goal_prefix: 'payment',
            answers: [
              { id: 4, answer_text: 'Рассрочка', answer_value: 'rassrochka' },
              { id: 5, answer_text: 'Ипотека', answer_value: 'ipoteka' },
              { id: 6, answer_text: 'Наличные', answer_value: 'nalichka' }
            ]
          },
          {
            id: 3,
            question_text: 'Когда планируете покупать?',
            metrika_goal_prefix: 'timing',
            answers: [
              { id: 7, answer_text: 'В ближайшее время', answer_value: 'now' },
              { id: 8, answer_text: 'Через полгода', answer_value: '6months' },
              { id: 9, answer_text: 'Через год', answer_value: '1year' }
            ]
          }
        ]
      });
      setIsLoading(false);
    } catch (error) {
      toast.error('Ошибка загрузки квиза');
      console.error(error);
    }
  };

  const selectAnswer = (questionId: number, answerId: number) => {
    setAnswers({ ...answers, [questionId]: answerId });

    const question = quiz?.questions[currentStep];
    const answer = question?.answers.find(a => a.id === answerId);

    // Отправка цели в Яндекс.Метрику
    if (quiz?.yandex_metrika_id && question && answer) {
      const goalName = `${question.metrika_goal_prefix}_${answer.answer_value}`;
      sendYandexMetrikaGoal(goalName);
    }
  };

  const sendYandexMetrikaGoal = (goalName: string) => {
    if (typeof (window as any).ym !== 'undefined' && quiz?.yandex_metrika_id) {
      (window as any).ym(quiz.yandex_metrika_id, 'reachGoal', goalName);
      console.log('Цель отправлена:', goalName);
    }
  };

  const nextStep = () => {
    if (!quiz) return;

    const currentQuestion = quiz.questions[currentStep];
    if (!answers[currentQuestion.id]) {
      toast.error('Выберите вариант ответа');
      return;
    }

    if (currentStep < quiz.questions.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      setCurrentStep(currentStep + 1); // Шаг контактов
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const submitQuiz = async () => {
    if (!contactInfo.name || !contactInfo.phone) {
      toast.error('Заполните имя и телефон');
      return;
    }

    try {
      // Формируем segment_key из ответов
      const segmentParts: string[] = [];
      quiz?.questions.forEach(q => {
        const answerId = answers[q.id];
        const answer = q.answers.find(a => a.id === answerId);
        if (answer) {
          segmentParts.push(answer.answer_value);
        }
      });
      const segment_key = segmentParts.join('_');

      // TODO: Отправка на backend
      console.log('Quiz submission:', {
        quiz_id: quiz?.id,
        answers,
        contactInfo,
        segment_key
      });

      // Отправка финальной цели в Метрику
      sendYandexMetrikaGoal('quiz_complete');

      setIsComplete(true);
      toast.success('Спасибо! Мы свяжемся с вами в ближайшее время');
    } catch (error) {
      toast.error('Ошибка отправки данных');
      console.error(error);
    }
  };

  const getProgress = () => {
    if (!quiz) return 0;
    return ((currentStep + 1) / (quiz.questions.length + 1)) * 100;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center">
        <div className="text-white text-xl">Загрузка...</div>
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center">
        <div className="text-white text-xl">Квиз не найден</div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center p-4">
        <Card className="bg-white/5 backdrop-blur border-white/10 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-white mb-2">Спасибо!</h2>
            <p className="text-slate-300">
              Ваша заявка принята. Мы свяжемся с вами в ближайшее время с подборкой квартир.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentQuestion = currentStep < quiz.questions.length ? quiz.questions[currentStep] : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-3xl py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">{quiz.title}</h1>
          <p className="text-slate-300">{quiz.description}</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
              style={{ width: `${getProgress()}%` }}
            />
          </div>
          <p className="text-sm text-slate-400 mt-2 text-center">
            Шаг {currentStep + 1} из {quiz.questions.length + 1}
          </p>
        </div>

        {/* Question Card */}
        <Card className="bg-white/5 backdrop-blur border-white/10 mb-6">
          <CardContent className="p-8">
            {currentQuestion ? (
              <>
                <h2 className="text-2xl font-bold text-white mb-6 text-center">
                  {currentQuestion.question_text}
                </h2>
                <div className="grid gap-4">
                  {currentQuestion.answers.map((answer) => (
                    <button
                      key={answer.id}
                      onClick={() => selectAnswer(currentQuestion.id, answer.id)}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${
                        answers[currentQuestion.id] === answer.id
                          ? 'border-blue-500 bg-blue-500/20 text-white'
                          : 'border-white/20 bg-white/5 text-slate-300 hover:border-white/40 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-lg">{answer.answer_text}</span>
                        {answers[currentQuestion.id] === answer.id && (
                          <Icon name="CheckCircle" size={24} className="text-blue-400" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                <h2 className="text-2xl font-bold text-white mb-6 text-center">
                  Оставьте контакты
                </h2>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-slate-300 mb-2 block">Ваше имя *</label>
                    <Input
                      value={contactInfo.name}
                      onChange={(e) => setContactInfo({ ...contactInfo, name: e.target.value })}
                      placeholder="Иван"
                      className="bg-white/10 border-white/20 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-slate-300 mb-2 block">Телефон *</label>
                    <Input
                      value={contactInfo.phone}
                      onChange={(e) => setContactInfo({ ...contactInfo, phone: e.target.value })}
                      placeholder="+7 (999) 123-45-67"
                      className="bg-white/10 border-white/20 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-slate-300 mb-2 block">Email</label>
                    <Input
                      value={contactInfo.email}
                      onChange={(e) => setContactInfo({ ...contactInfo, email: e.target.value })}
                      placeholder="ivan@example.com"
                      className="bg-white/10 border-white/20 text-white"
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex justify-between">
          <Button
            onClick={prevStep}
            disabled={currentStep === 0}
            variant="outline"
            className="border-white/20 text-white hover:bg-white/10"
          >
            <Icon name="ChevronLeft" size={20} className="mr-2" />
            Назад
          </Button>
          {currentQuestion ? (
            <Button
              onClick={nextStep}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              Далее
              <Icon name="ChevronRight" size={20} className="ml-2" />
            </Button>
          ) : (
            <Button
              onClick={submitQuiz}
              className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
            >
              <Icon name="Send" size={20} className="mr-2" />
              Отправить заявку
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
